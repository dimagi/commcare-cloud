# Splitting a pillow

In some cases a pillow may contain multiple processors. It is sometimes desirable to split
up the processors into individual OS processes. The most compelling reason to do this is if
one of the processors is much slower than the others. In this case having the slow processor
separated allows the other's to process at a faster pace. It may also be possible to deploy
additional processing capacity for the slow one.

The the following steps we will be splitting the `FormSubmissionMetadataTrackerProcessor`
out from the `xform-pillow`.

The `xform-pillow` has multiple processors as can be seen from the
[CommCare docs](https://commcare-hq.readthedocs.io/pillows.html#corehq.pillows.xform.get_xform_pillow).
The `FormSubmissionMetadataTrackerProcessor` can be disabled by setting
`RUN_FORM_META_PILLOW` to `False` in the Django settings file. We can also see that the
`FormSubmissionMetadataTrackerProcessor` is used by the `FormSubmissionMetadataTrackerPillow`.

So in order to split the `FormSubmissionMetadataTrackerProcessor` into its own pillow process
we need to do the following:

1. Update the environment configuration

    * Add the new pillow to `<env>/app-processes.yml`

        ```yaml
        pillows:
          'pillow_host_name':
            FormSubmissionMetadataTrackerPillow:
              num_processes: 3
        ```

    * Update the `RUN_FORM_META_PILLOW` to disable the processor in the current pillow:

        ```yaml
        localsettings:
          RUN_FORM_META_PILLOW: False
        ```

2. Stop the current pillow

    ```bash
    cchq <env> service pillowtop stop --only xform-pillow
    ```

3. Create new checkpoints for the new pillow

    ```bash
    cchq <env> django-manage --tmux split_pillow_checkpoints xform-pillow FormSubmissionMetadataTrackerPillow
    ```

   Note: `--tmux` is necessary to allocate a terminal for the command which allows you to respond to any
   confirmation prompts.

4. Deploy the new pillow

    ```bash
    cchq <env> update-supervisor-confs
    ```

5. Ensure all the pillows are started

    ```bash
    cchq <env> service pillowtop start
    ```