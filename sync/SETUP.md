# The notebook: syncing hearts and passes through a Google Sheet

Five minutes, once. Needs your Google account.

1. Go to https://sheets.new and create a blank spreadsheet. Name it after the closet, e.g. "Becca's Closet notebook".
2. In the sheet, choose **Extensions → Apps Script**. Delete the sample code in the editor,
   paste the whole contents of `sync/Code.gs`, and press the save icon.
3. Click **Deploy → New deployment**. Click the gear next to "Select type" and choose **Web app**.
   - Description: closet notebook
   - Execute as: **Me**
   - Who has access: **Anyone**
   Click **Deploy**, approve the permissions prompt (it only asks for access to this spreadsheet),
   and copy the **Web app URL**. It ends in `/exec`.
   Google will show a "Google hasn't verified this app" screen: click **Advanced**, then
   "Go to … (unsafe)", then **Allow**. The app is your own script; the first line of the code
   limits its permission to this one spreadsheet.
4. Paste that URL into `config.js` as the value of `"syncUrl"`, commit and push.
   (Or hand the URL to Claude and it will do this step.) The `"notebookKey"` next to it names her list
   inside the sheet, so one sheet could serve more than one closet.
5. Open the closet, heart something, and look at the sheet: an `events` tab fills with one row per
   action and a `latest` tab lists what is currently saved or marked not for me, newest change first.
   (If the `latest` tab still has old column headings from an earlier version, delete that tab; the script
   recreates it on the next tap.)

Notes
- If you ever edit `Code.gs`, choose **Deploy → Manage deployments → edit → Version: New version**.
  A plain save does not update the live web app.
- The site keeps working without the notebook. If the URL is empty or Google is unreachable, hearts and
  passes stay in the browser as before, and any actions made offline are delivered the next time the
  page opens with a connection.
- To pause syncing, empty the `content` attribute again and push.
