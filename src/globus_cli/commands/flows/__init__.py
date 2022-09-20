from globus_cli.parsing import group


@group(
    "flows",
    lazy_subcommands={
        "list": (".list", "list_command"),
    },
    hidden=True,
)
def flows_command():
    """Interact with the Globus Flows service"""
