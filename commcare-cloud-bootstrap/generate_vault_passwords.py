import argparse
import commcare_cloud_bootstrap as ccb


parser = argparse.ArgumentParser()
parser.add_argument("--env")

args = parser.parse_args()

environment = ccb.get_environment(args.env)
saveToVault = ccb.save_vault_yml(environment)
