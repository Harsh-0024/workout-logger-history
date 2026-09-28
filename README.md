# Workout Logger history

A live look at how [Workout Logger](https://github.com/Harsh-0024/workout_logger_) is being built: every commit, branch and merge, a commit calendar, streaks and lines of code.

**See it:** https://harsh-0024.github.io/workout-logger-history/

The page rebuilds every night at 2:30 AM IST, and whenever this repository's `main` is pushed. To rebuild it now, open the **Actions** tab, pick **Build History Page** and press **Run workflow**.

- `page/template.html` is the page itself.
- `scripts/build_git_history.py` reads Workout Logger's history and fills the page in.
- `.github/workflows/nightly.yml` runs the script and publishes the result.

Nothing here touches the Workout Logger repository or its deploys. It only reads its public history.
