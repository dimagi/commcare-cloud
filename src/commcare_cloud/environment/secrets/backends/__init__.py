from commcare_cloud.environment.secrets.backends.ansible_vault.main import AnsibleVaultSecretsBackend

all_secrets_backends = [
    AnsibleVaultSecretsBackend,
]
all_secrets_backends_by_name = {
    cls.name: cls
    for cls in all_secrets_backends
}
