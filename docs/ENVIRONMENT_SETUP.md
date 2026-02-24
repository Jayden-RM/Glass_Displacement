# Environment Setup (Windows)

This guide walks through installing Python and configuring the development environment to run the laser system.

---

## 1. Install Required Software

Download and install the following:

1. Anaconda  
   https://www.anaconda.com/download

2. Visual Studio Code  
   https://code.visualstudio.com/download

3. GitHub Desktop  
   https://desktop.github.com/

4. Create a GitHub account using your TPV email  
   https://github.com/

---

## 2. Create the Standard Anaconda Environment

1. Open **Anaconda Navigator**
2. Go to **Environments**
3. Click **Create**
4. Name the environment:

   ```
   standard
   ```

5. Check the Python box and use the default version
6. Click **Create**

---

## 3. Configure GitHub Desktop

1. Open GitHub Desktop
2. Log in with your GitHub account
3. Accept default settings

---

## 4. Prepare VS Code + Python Kernel

1. Open **VS Code**
2. File → Open Folder
3. Navigate to:

   ```
   Users/Documents/Github
   ```

4. Create a new file:

   ```
   temp.ipynb
   ```

5. In the first cell, type:

   ```python
   import os
   ```

6. Click **Select Kernel** (top right)
7. Choose:

   ```
   Python Environments → standard
   ```

8. Run the notebook (Shift+Enter) and accept prompts to install:

   - Python components  
   - ipykernel  

9. Verify the notebook runs without errors
10. Delete `temp.ipynb`

---

## 5. Recommended VS Code Extensions

- autoDocstring  
- Black Formatter  
- indent-rainbow  
- Dark theme (optional)

---

## 6. Request Repository Access

Send a Slack message to the repository maintainer (currently Jayden: GitHub username: jaydenig) requesting access to the desired repository.

---

## 7. Clone the Repository

1. Open **GitHub Desktop**
2. File → Clone Repository
3. Select the invited repository  
4. Download to the default GitHub folder in Documents

---

## 8. Create Project Environment

1. Open **Anaconda Navigator**
2. Go to **Environments**
3. Clone the `standard` environment
4. Name the new environment as desired (`<new_env>`)

---

### Install the package in editable mode

1. Open the environment terminal (ipykernel terminal)
2. Navigate to the repository root (where `setup.py` is located):

   ```bash
   cd <path_to_repo>
   ```

3. Install:

   ```bash
   pip install -e .
   ```

This installs the package in editable mode so local changes take effect immediately.

---

## 9. Check for Path-Specific Settings

Before running the program:

- Review any `.yaml` files (preferences/config)
- Review any `.bat` files (Windows launch scripts)

Typical batch activation format:

```
call C:/Users/<username>/anaconda3/Scripts/activate.bat <environment>
start python <program>
```

---

# Updating an Existing Program

1. Open **GitHub Desktop**
2. Select the repository
3. Click **Fetch Origin**
4. Click **Pull Origin**

⚠️ **Do NOT Push**

If prompted to stash changes:

- Accept the stash
- Discard local changes if appropriate

---

## Notes

If setup fails at any step, contact a team member for assistance.
