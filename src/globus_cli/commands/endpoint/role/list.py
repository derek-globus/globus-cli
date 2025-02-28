import globus_sdk

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command, endpoint_id_arg
from globus_cli.termio import formatted_print


@command(
    "list",
    short_help="List roles on an endpoint",
    adoc_output="""Textual output has the following fields:

- 'Principal Type'
- 'Role ID'
- 'Principal'
- 'Role'

The principal is a user or group ID, and the principal type says which of these
types the principal is. The term "Principal" is used in the sense of "a
security principal", an entity which has some privileges associated with it.
""",
    adoc_examples="""Show all roles on 'ddb59aef-6d04-11e5-ba46-22000b92c6ec':

[source,bash]
----
$ globus endpoint role list 'ddb59aef-6d04-11e5-ba46-22000b92c6ec'
----
""",
)
@endpoint_id_arg
@LoginManager.requires_login(LoginManager.AUTH_RS, LoginManager.TRANSFER_RS)
def role_list(*, login_manager: LoginManager, endpoint_id):
    """
    List the assigned roles on an endpoint.

    You must have sufficient privileges to see the roles on the endpoint.
    """
    transfer_client = login_manager.get_transfer_client()
    roles = transfer_client.endpoint_role_list(endpoint_id)

    resolved_ids = globus_sdk.IdentityMap(
        login_manager.get_auth_client(),
        (x["principal"] for x in roles if x["principal_type"] == "identity"),
    )

    def principal_str(role):
        principal = role["principal"]
        if role["principal_type"] == "identity":
            try:
                return resolved_ids[principal]["username"]
            except KeyError:
                return principal
        if role["principal_type"] == "group":
            return f"https://app.globus.org/groups/{principal}"
        return principal

    formatted_print(
        roles,
        fields=[
            ("Principal Type", "principal_type"),
            ("Role ID", "id"),
            ("Principal", principal_str),
            ("Role", "role"),
        ],
    )
