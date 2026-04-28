# Context

When running cchq <env> --control deploy, our deploy script makes GitHub API calls to push tags.
This requires prompting the user for their GitHub PAT, and this interactivity slows down the process.

# Goal

Have the script push tags without needing user input.

# Proposal

Instead of using the GitHub API to push tags, use a native git push.
Because we are already agent-forwarding in the SSH connection,
we should be able to do this push using our own forwarded credentials,
as long as the git connection is SSH and not HTTPS.
