import re
import subprocess

# will change from assignment to assignment, will return a graded rubric of the assignment
def grade(info, rubric, student_id, submission_dir_name):
    def helper_input(prompt):
        user_input = input(prompt)
        if user_input in (
            "y",
            "Y",
            "yes",
            "Yes",
        ):
            return True
        elif user_input == "q":
            raise StopIteration()
        else:
            return False

    rubric_assessment = {}

    if info["workflow_state"] == "submitted":
        # check filename and header
        file_name = info["file_name"]
        cur_criterion = rubric["File Name / Header"]
        file_name_correct = re.search("^Initials(-[0-9]*)?.py$", file_name)
        with open(f"{submission_dir_name}{student_id}", "r") as f:
            print(f.read())
        comment = ""
        header_correct = helper_input("Does this header look good? (y/n) ")
        if file_name_correct and header_correct:
            verdict = "Correct file name AND header comment"
        elif file_name_correct:
            verdict = "Correct file name OR correct header comment"
            comment = "header incorrect"
        elif header_correct:
            verdict = "Correct file name OR correct header comment"
            comment = "file name incorrect"
        else:
            verdict = "No Marks"
            comment = "file name and header incorrect"

        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

        # check if program ran successfully
        completed_process = subprocess.run(
            ["python", f"{submission_dir_name}{student_id}"]
        )
        cur_criterion = rubric["Compiles and runs"]
        comment = ""
        if completed_process.returncode == 0:
            verdict = "Full Marks"
        else:
            verdict = "No Marks"
            comment = "failed to run"
        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

        # check initials
        cur_criterion = rubric["Initials"]
        comment = ""
        print(f"The student name is {info['name']}")
        initials_correct = helper_input(f"Are the initials correct? (y/n) ")
        letters_correct = helper_input(f"Are the letters correct? (y/n) ")
        if initials_correct and letters_correct:
            verdict = (
                "Correct initials AND each letter is made up of the correct letters"
            )
        elif initials_correct:
            verdict = (
                "Correct initials OR each letter is made up of the correct letters"
            )
            comment = "letters incorrect"
        elif letters_correct:
            verdict = (
                "Correct initials OR each letter is made up of the correct letters"
            )
            comment = "initials incorrect"
        else:
            verdict = "No Marks"
            comment = "letters and initials incorrect"

        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

        # check periods
        cur_criterion = rubric["Periods"]
        comment = ""
        correct = helper_input(f"Are the periods correct? (y/n) ")
        if correct:
            verdict = 'Each letter is followed by a period drawn using four "."'
        else:
            verdict = "No Marks"
            comment = "periods incorrect"

        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

        # check dimensions of letters
        cur_criterion = rubric["Dimensions of letters"]
        comment = ""
        correct = helper_input(f"Are the dimensions of the letters correct? (y/n) ")
        if correct:
            verdict = "Every letter should be 12 characters wide and 10 lines high"
        else:
            verdict = "No Marks"
            comment = "dimensions of characters incorrect"

        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

        # check empty line and columns
        cur_criterion = rubric["Empty line and columns"]
        comment = ""
        correct = helper_input(f"Are there empty lines above and below? (y/n) ")
        if correct:
            verdict = (
                "Correct number of empty columns AND correct number of empty lines"
            )
        else:
            verdict = "No Marks"
            comment = "need empty lines above and below output"

        rating = cur_criterion["ratings"][verdict]
        rubric_assessment[cur_criterion["id"]] = {
            "rating_id": rating["id"],
            "comments": comment,
            "points": rating["points"],
        }

    return rubric_assessment