import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import IdentityType, ParsedIdentity, command
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print
from globus_cli.types import FIELD_LIST_T

REJECTED_USER_FIELDS: FIELD_LIST_T = [
    ("Group ID", "group_id"),
    ("Rejected User ID", "identity_id"),
    ("Rejected User Username", "username"),
]


@command("reject", short_help="Reject a member from a group")
@click.argument("group_id", type=click.UUID)
@click.argument("user", type=IdentityType())
@LoginManager.requires_login(LoginManager.GROUPS_RS)
def member_reject(*, group_id: str, user: ParsedIdentity, login_manager: LoginManager):
    """
    Reject a pending member from a group.

    The USER argument may be an identity ID or username (whereas the group must be
    specified with an ID).
    """
    auth_client = login_manager.get_auth_client()
    groups_client = login_manager.get_groups_client()
    identity_id = auth_client.maybe_lookup_identity_id(user.value)
    if not identity_id:
        raise click.UsageError(f"Couldn't determine identity from user value: {user}")
    actions = {"reject": [{"identity_id": identity_id}]}
    response = groups_client.batch_membership_action(group_id, actions)
    if not response.get("reject", None):
        try:
            raise ValueError(response["errors"]["reject"][0]["detail"])
        except (IndexError, KeyError):
            raise ValueError("Could not reject the user from the group")
    formatted_print(
        response,
        text_format=FORMAT_TEXT_RECORD,
        fields=REJECTED_USER_FIELDS,
        response_key=lambda data: data["reject"][0],
    )
