# Sync code to feature
1. `git fetch origin`
2. `git rebase origin/<remote_branch>`
3. Fix conflict nếu có
    * `git add .`
    * `git rebase --continue`

    * `git rebase --abort`
4. `git push --force-with-lease`

# Sửa commit cuối
1. `git commit --amend -m "Nội dung commit message mới"`
2. `git push --force-with-lease`

# Gộp code vào commit cuối
1. `git add .`
2. `git commit --amend --no-edit`
3. `git push --force-with-lease`