from commcare_cloud.environment.secrets.backends.ansible_vault.main import AnsibleVaultSecretsBackend
from commcare_cloud.environment.secrets.backends.aws_secrets.main import AwsSecretsBackend

all_secrets_backends = [
    AnsibleVaultSecretsBackend,
    AwsSecretsBackend,
]
all_secrets_backends_by_name = {
    cls.name: cls
    for cls in all_secrets_backends
}
