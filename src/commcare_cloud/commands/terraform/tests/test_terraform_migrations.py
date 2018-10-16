from commcare_cloud.commands.terraform.terraform_migrate_state import get_migrations


def test_numbering():
    """
    Test that terraform state migration files are numbered correctly

    starting at 1, with no gaps and no repeats
    """
    migrations = get_migrations()
    numbers = [migration.number for migration in migrations]
    if numbers:
        assert numbers == list(range(1, numbers[-1] + 1)), numbers
