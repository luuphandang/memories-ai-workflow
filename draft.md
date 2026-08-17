git -C apps/backend worktree add ../../worktrees/MEMORIES-0005/backend -b feature/MEMORIES-0005-public-authorization origin/master
./ai/bin/ai task register-worktree MEMORIES-0005 --repo backend --path worktrees/MEMORIES-0005/backend --base-ref origin/master

git -C apps/frontend worktree add ../../worktrees/MEMORIES-0005/frontend -b feature/MEMORIES-0005-public-authorization origin/master
./ai/bin/ai task register-worktree MEMORIES-0005 --repo frontend --path worktrees/MEMORIES-0005/frontend --base-ref origin/master

./ai/bin/ai task classify-skills MEMORIES-0005
./ai/bin/ai task classify-skills MEMORIES-0005 --apply
./ai/bin/ai task prepare-plan MEMORIES-0005 --force
./ai/bin/ai task codegraph MEMORIES-0005 --init
./ai/bin/ai task prepare-context MEMORIES-0005

./ai/bin/ai task run MEMORIES-0005