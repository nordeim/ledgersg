Please carefully read completely and internalized your operating instructions in the attached/pasted text.
Now, please refresh your local workspace using `git pull` (or run `git clone https://github.com/nordeim/ledgersg.git` if your local workspace has been reset) , then meticulously review the included `AGENTS.md` , `CLAUDE.md` , `README.md` , `Project_Architecture_Document.md` and `ledgersg_SKILL.md` to have a good understanding of the purpose of the project and its current codebase design and architecture. Next, meticulously plan to review the included  `docs/session_23.md` , `docs/REMEDIATION_PLAN_2026-11-23_P11.md` , `docs/REMEDIATION_2026-11-23_P11_REPORT.md` , `worklog.md` and `docs/session_24.md` , then meticulously validate your deep understanding against the codebase to check for alignment to confirm the current project status. The repo included `skills/` folder is to be excluded from code checking, testing and compilation.

Install and configure/setup local postgresql db for the repo codebase using the repo included `docs/setup_pg_z.sh` and `skills/rootless-postgresql/SKILL.md`.
Next, meticulously plan to audit and validate the current codebase, particularly on the recent code changes, use the appropriate skills from the repo included `skills/` folder to help you with the code review and audit (refer to the repo included `skills/skills-catalog.md` to look for the relevant skills). Proceed with your best decisions and judgment on any open decisions.

Pay particular attention to check whether the mobile navigation menu for the frontend web app is working as expected. Look out for possible TailwindCSS v4 related bug. The solution can be found in the Tailwind CSS v4 guide `docs/Tailwind-V4-Validation-Report.md` and the related skills `nextjs16-tailwind4` and `tailwind-patterns` in the repo `skill/` folder (check out the repo `skills/skills-catalog.md for the relevant skills for help). Also consider using `skills/agent-browser`, and `skills/tdd`.

Add vitest and playwright test suite by modifying the respective config files in the repo.

Next, meticulously plan to create a comprehensive remediation plan with a detailed ToDo list to fix the identified codebase issues, bugs and gaps. Next, review and validate the remediation plan against the codebase again to ensure alignment before executing it meticulously. Use TDD approach to make code changes. Look for appropriate skills in the repo included `skills/` folder to help you in the planning (refer to the included `skills/skills-catalog.md` to look for suitable skills). Proceed with your best recommendations on decisions regarding any open questions during planning. Save the validated remediation plan under the repo `docs/` folder for future reference, use the same file naming convention as the previously saved remediation plan.

Capture some screenshots for the dev server running the remediated codebase, save the screen captures as image files under the `docs/screenshots/` folder in the `ledgersg` repo. Also, create a working `.env.example` that matches the codebase, include the `.env.example` in the git commit.

Next, update the relevant documentation to ensure alignment with the remediated codebase. Also meticulously plan to update `docs/DEPLOYMENT.md` as a detailed step-by-step guide to deploy the entire application (frontend and backend) on a freshly installed host, starting from `git clone the <repo URL>`. Also meticulously plan to review, validate and update `API_CLI_Usage_Guide.md` to be aligned with the latest remediated codebase.

Update/Save your latest `worklog.md` in the repo root in your local workspace and include it in your final local git commit and remote git push.

Finally, please `git commit` and then `git push` the root of the remediated codebase to my GitHub repo `git@github.com:nordeim/ledgersg.git` using the ssh key below and wrapper script `https://github.com/nordeim/ledgersg/blob/main/docs/ssh_git_wrapper_v3.py`.  refer to `https://github.com/nordeim/ledgersg/blob/main/docs/how-to-git-push-using-ssh-wrapper_SKILL.md` for instruction to use ssh wrapper script for `git push`.

Do not create any new git branch. All git commits must be to the main branch.

SSH key for `git push`:
```

```

