import subprocess

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.github import GITHUB_KNOWN_HOSTS


class RefreshGithubKnownHosts(CommandBase):
    command = 'refresh-github-known-hosts'
    help = (
        "Refetch github.com's SSH host keys via ssh-keyscan and write them "
        "to the bundled known_hosts file used for deploy tag pushes. "
        "Run this if GitHub rotates its host keys."
    )

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        result = subprocess.run(
            ["ssh-keyscan", "-t", "rsa,ecdsa,ed25519", "github.com"],
            check=True, capture_output=True, text=True,
        )
        keys = sorted(
            line for line in result.stdout.splitlines()
            if line and not line.startswith("#")
        )
        GITHUB_KNOWN_HOSTS.write_text("".join(line + "\n" for line in keys))
        self.log(f"Wrote {GITHUB_KNOWN_HOSTS}")
        fingerprints = subprocess.run(
            ["ssh-keygen", "-lf", str(GITHUB_KNOWN_HOSTS)],
            check=True, capture_output=True, text=True,
        ).stdout
        print()
        print("Verify these fingerprints against https://docs.github.com/en/"
              "authentication/keeping-your-account-and-data-secure/"
              "githubs-ssh-key-fingerprints :")
        print()
        print(fingerprints)
