import numpy as np
import requests
import json
from pathlib import Path
from importlib import import_module

# grab config json from file
def get_config():
    if Path("config.json").is_file():
        with open("config.json") as f:
            config = json.load(f)
            needed_params = ["canvas_api_token", "beginning", "end"]
            for param in needed_params:
                if param not in config:
                    raise ValueError("config.json missing some fields, look at README")
            return config
    else:
        raise ValueError("Need a config.json file, look at README")


# grab course ID
def get_course_id(headers):
    response = requests.get(
        f"https://utexas.instructure.com/api/v1/courses/?enrollment_type=ta&enrollment_state=active",
        headers=headers,
    )
    return response.json()[0]["id"]


# grabs correct assignment to grade
def find_assignment(headers, course_id):

    response = requests.get(
        f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments?per_page=1000",
        headers=headers,
    )
    idx_to_assignment = {
        i: assignment
        for i, assignment in enumerate(
            [
                assignment
                for assignment in response.json()
                if assignment["needs_grading_count"] > 0
            ]
        )
    }

    for k, v in idx_to_assignment.items():
        print(f"{k}: {v['name']}")

    assignment_idx = int(input("Enter the index of the assignment you want to grade: "))

    while assignment_idx not in idx_to_assignment:
        print("invalid index")
        assignment_idx = int(
            input("Enter the index of the assignment you want to grade: ")
        )

    mod = import_module(
        f"grading_functions.{idx_to_assignment[assignment_idx]['name']}", "."
    )
    grading_function = getattr(mod, "grade")

    return idx_to_assignment[assignment_idx]["id"], grading_function


# grabs students from this course
def get_students(headers, course_id):
    if Path("students.npy").is_file():
        all_students = np.load("students.npy", allow_pickle=True)
    else:
        has_more = True
        page = 1
        all_students = []

        while has_more:
            response = requests.get(
                f"https://utexas.instructure.com/api/v1/courses/{course_id}/users?enrollment_type=student&page={page}&per_page=100",
                headers=headers,
            )
            students = response.json()
            has_more = "next" in response.links
            page += 1
            all_students.extend(students)

        np.save("students", all_students)

    return all_students


# downloads the submissions of all of your students for this assignment and returns metadata about those files
def download_submissions(
    headers, course_id, assignment_id, all_students, beginning, end
):
    subdir_name = f"submissions/{assignment_id}"
    Path(subdir_name).mkdir(parents=True, exist_ok=True)

    Path("metadata").mkdir(exist_ok=True)

    # maps student_id to original file name, and seconds late, and workflow state, student_name
    if Path(f"metadata/{assignment_id}.npy").is_file():
        metadata = np.load(f"metadata/{assignment_id}.npy", allow_pickle=True).item()
    else:
        metadata = {}

    for student in all_students:
        last_name = student["sortable_name"].split()[0]
        if "," in last_name:
            last_name = last_name[:-1]
        if beginning <= last_name <= end and not student["id"] in metadata:
            response = requests.get(
                f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{student['id']}",
                headers=headers,
            )
            student_info = {}
            student_info["name"] = student["name"]
            student_info["workflow_state"] = response.json()["workflow_state"]

            if student_info["workflow_state"] == "submitted":
                student_info["seconds_late"] = int(response.json()["seconds_late"])
                url = response.json()["attachments"][0]["url"]
                response = requests.get(url, headers=headers)
                student_info["file_name"] = response.headers[
                    "content-disposition"
                ].split("filename=")[1][1:-1]
                with open(f"{subdir_name}/{student['id']}", "wb") as f:
                    f.write(response.content)
            elif student_info["workflow_state"] == "unsubmitted":
                student_info["file_name"] = ""
                student_info["seconds_late"] = -1
            metadata[student["id"]] = student_info
    np.save(f"metadata/{assignment_id}", metadata)
    return metadata


def get_rubric(headers, course_id, assignment_id):
    response = requests.get(
        f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}",
        headers=headers,
    )
    rubric = response.json()["rubric"]
    for criterion in rubric:
        criterion["ratings"] = {
            rating["description"]: rating for rating in criterion["ratings"]
        }
    return {criterion["description"]: criterion for criterion in rubric}


# grade the submissions
def grade_submissions(assignment_id, rubric, metadata, grade_function):

    Path("grades").mkdir(exist_ok=True)
    # grades maps student id to rubric assessment
    if Path(f"grades/{assignment_id}.npy").is_file():
        grades = np.load(f"grades/{assignment_id}.npy", allow_pickle=True).item()
    else:
        grades = {}
    submission_dir_name = f"submissions/{assignment_id}/"
    for student_id, cur_info in metadata.items():
        # already graded
        if student_id in grades:
            continue
        try:
            rubric_assessment = grade_function(
                cur_info, rubric, student_id, submission_dir_name
            )
        except StopIteration:
            break
        grades[student_id] = rubric_assessment

    np.save(f"grades/{assignment_id}.npy", grades)
    return grades


# flattens dict for http format and adds necessary information
def format_for_http(rubric_assessment, student_id):
    data = {}
    data["rubric_assessment[user_id]"] = str(student_id)
    data["rubric_assessment[assessment_type]"] = "student_id"
    for criterion_id, field_to_value in rubric_assessment.items():
        for field, value in field_to_value.items():
            data[f"rubric_assessment[{criterion_id}][{field}]"] = str(value)
    return data


# publishes grades
def publish(grades, course_id, assignment_id, headers, metadata):
    for student_id in grades:
        if grades[student_id]:
            data = format_for_http(grades[student_id], student_id)
            response = requests.put(
                f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}",
                headers=headers,
                data=data,
            )
            # if late, deduct points and put comment
            if metadata[student_id]["seconds_late"] > 0:
                days_late = metadata[student_id]["seconds_late"] // 86400 + 1
                response = requests.put(
                    f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}",
                    headers=headers,
                    data={
                        "submission[posted_grade]": response.json()["score"]
                        * (0.9 ** days_late),
                        "comment[text_comment]": f"{days_late} day(s) late",
                    },
                )
        else:
            # no submission
            data = {"submission[posted_grade]": 0}
            response = requests.put(
                f"https://utexas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}",
                headers=headers,
                data=data,
            )


def main():
    config = get_config()
    headers = {"Authorization": "Bearer " + config["canvas_api_token"]}
    course_id = get_course_id(headers)
    assignment_id, grading_function = find_assignment(headers, course_id)

    all_students = get_students(headers, course_id)
    beginning = config["beginning"]
    end = config["end"]
    metadata = download_submissions(
        headers, course_id, assignment_id, all_students, beginning, end
    )
    rubric = get_rubric(headers, course_id, assignment_id)
    grades = grade_submissions(assignment_id, rubric, metadata, grading_function)
    decision = input("p to publish grades, anything else to exit\n")
    if decision == "p":
        publish(grades, course_id, assignment_id, headers, metadata)


if __name__ == "__main__":
    main()
