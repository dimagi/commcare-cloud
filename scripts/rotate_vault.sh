#!/usr/bin/env bash

init_keepass () {
    # Locate keepassxc-cli or fail with error
    if [[ "$OSTYPE" == "darwin"* ]]; then
        KEE_PASS=/Applications/KeePassXC.app/Contents/MacOS/keepassxc-cli
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        KEE_PASS=`which keepassxc-cli`
    fi

    if [ ! -x $KEE_PASS ]; then
        echo "KeePassXC was not found. Please go to https://keepassxc.org to install it"
        exit 1
    fi
}

prompt_for_password () {
    echo "Enter password to unlock $KEE_PASS_DB:"
    read -s KEE_PASS_DB_PASS
}

store_password () {
    local password=$1

    printf "$KEE_PASS_DB_PASS\n$KEE_PASS_DB_PASS" | $KEE_PASS db-create "$TEMP_DATABASE" -p > /dev/null 2>&1
    printf "$KEE_PASS_DB_PASS\n$password" | $KEE_PASS add "$TEMP_DATABASE" $TEMP_KEY -p -q 
}

retrieve_password () {
    echo "$KEE_PASS_DB_PASS"|$KEE_PASS show "$TEMP_DATABASE" "$TEMP_KEY" -a password -q
}

update_keepass () {
    if [ -z "$GENERATED_PASS" ]; then
        GENERATED_PASS=`retrieve_password`
    fi

    CURRENT_TIME=`date -u`
    printf "$KEE_PASS_DB_PASS\n$GENERATED_PASS" | $KEE_PASS edit "$KEE_PASS_DB" "$KEY_PATH" -p \
        --notes "Rotated on $CURRENT_TIME by `whoami`" -q

    if [ $? -ne 0 ]; then
        exit 1
    fi
    

    # Remove the temporary database -- there is no need for it anymore
    rm "$TEMP_DATABASE"
}

resume () {
    if [ ! -f "$TEMP_DATABASE" ]; then
        echo "No previous run detected to resume from"
        exit 1
    fi
    init_keepass
    prompt_for_password
    update_keepass
}

check_for_previous_run () {
    if [ -e "$TEMP_DATABASE" ]; then
        echo "Data from previous run found. You can resume with the --resume flag. Are you sure you want a new run?"
        echo "Type 'y' to continue"
        read -n1 CONTINUE
        echo
        if [ $CONTINUE == "y" ]; then
            rm "$TEMP_DATABASE"
        else
            exit 1
        fi
    fi
}

rotate_vault_key () {
    init_keepass
    check_for_previous_run
    prompt_for_password

    # Read the current vault password from the keepass file
    CURRENT_PASS=`echo "$KEE_PASS_DB_PASS"|$KEE_PASS show "$KEE_PASS_DB" "$KEY_PATH" -a password -q`

    if [ -z $CURRENT_PASS ]; then
        echo "Invalid password"
        exit 1
    fi

    # Generate a new password
    GENERATED_PASS=`$KEE_PASS generate`  # Can add specific complexity requirements as args

    # Update the ansible vault
    printf "$CURRENT_PASS\n$GENERATED_PASS\n" | ansible-vault rekey \
        --vault-id scripts/echo_stdin-client.sh \
        --new-vault-id scripts/echo_stdin-client.sh \
        environments/swiss/vault.yml > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        echo "KeePass password does not match existing vault password"
        exit 1
    fi

    # Store the generated password in a temporary database for retrieval later
    store_password $GENERATED_PASS

    printf "Swiss vault has been updated. Please stage and commit the changes and create a PR.
    When the PR is approved, you can re-run this script with the --resume flag to update KeePass\n"

    # Could attempt to automate the PR at this point.
    # Ensure that only the vault is being changed and that master is up-to-date, however.

    echo "Type 'APPLY' to update the KeePass. If terminated, the KeePass can be updated at a later date by re-running this script with the --resume option"
    echo
    read CONTINUE

    if [ "$CONTINUE" == "APPLY" ]; then
        update_keepass
    else
        echo "Ending without updating the keepass with the new password. Run this script again with the --resume flag to complete the operation"
    fi
}

display_help () {
    echo "Usage: $0 <keepass file> [--resume]"
    echo "  <keepass file> should be the full path to the keepass database containing the swiss vault password"
    echo "  --resume should be specified after the rotation PR has been merged"
}

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    display_help
    exit 1
fi

KEE_PASS_DB=$1
KEY_PATH="swiss/Swiss ansible vault"
TEMP_DATABASE='.vault_rotation_db.kdbx'
TEMP_KEY="new_pass"

if [ $# -eq 2 ]; then
    if [ "$2" == "--resume" ]; then
        resume
    else
        display_help
        exit 1
    fi
else
    rotate_vault_key
fi
