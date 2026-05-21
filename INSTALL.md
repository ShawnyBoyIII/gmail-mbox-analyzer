# Simple Installation Guide (Mac Friendly!)

If you aren't a programmer and just want to run this app with a simple window to analyze your Gmail file, follow these steps!

## 1. Download Your Gmail Data
1. Go to [Google Takeout](https://takeout.google.com/).
2. Click "Deselect all", then scroll down and check **Mail**.
3. Scroll to the bottom and click **Next Step**, then **Create Export**.
4. Once Google emails you the link, download the `.zip` file.
5. Double-click the `.zip` file to extract it. Inside, you will find a `.mbox` file (usually named `All mail Including Spam and Trash.mbox`). This is the file you need.

## 2. Install Python (The Engine)
Your Mac needs a free program called Python to run this app.

1. Open your web browser and go to [python.org/downloads/macos](https://www.python.org/downloads/macos/).
2. Click the link for the **Latest Python 3 Release** and download the "macOS 64-bit universal2 installer".
3. Double-click the downloaded `.pkg` file and follow the standard installation steps.

## 3. Download This App
1. On this project's webpage (likely GitHub), look for a green **Code** button and click **Download ZIP**.
2. Double-click the downloaded ZIP file to extract it. It will create a folder (e.g., `gmail-mbox-analyzer-main`).
3. Move this folder somewhere easy to find, like your **Desktop**.

## 4. Run the App
Now, let's open the app!

1. Open the **Terminal** app on your Mac. (You can find it by pressing `Command + Space`, typing "Terminal", and pressing Enter).
2. Tell the Terminal to go to the folder you downloaded by typing `cd ` (with a space at the end), then drag and drop the folder from your Desktop directly into the Terminal window. It should look something like this:
   ```bash
   cd /Users/yourname/Desktop/gmail-mbox-analyzer-main
   ```
3. Press **Enter**.
4. Finally, type the following command and press **Enter**:
   ```bash
   python3 -m src.gmail_mbox_analyzer
   ```

A simple window will pop up! From there, you can click **Browse...** to select your `.mbox` file and click **Run Analysis**.
