In order for this to work, add your canvas api token to a config.json file. Formatted like this.

```javascript
{
  "canvas_api_token": "<ENTER YOUR TOKEN HERE>",
  "beginning": "Kli (replace with your beginning last name)",
  "end": "Lu (replace with your end last name)"
}
```

Your access token can be found on Canvas -> Account -> Settings -> New Access Token

To run, simply just run `python grade.py` and follow the given prompts.

If you are running into import issues, install everything found in requirements.txt.

Since grading can take a while, type q and enter for any grading prompt to quit out and save your progress.
