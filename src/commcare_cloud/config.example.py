# Optional GitHub API token used to get a higher rate limit on read-only
# diff/compare calls during deploy. The GITHUB_TOKEN environment variable
# is also honored. A token is no longer required for deploy tagging,
# which is now done via SSH using the user's forwarded agent credentials.

GITHUB_APIKEY = None
