from __future__ import annotations

import uuid

import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import IdentityType, ParsedIdentity, command
from globus_cli.termio import formatted_print

from ._common import build_invite_actions, get_invite_formatter


@command("accept", short_help="Accept an invitation")
@click.argument("group_id", type=click.UUID)
@click.option(
    "--identity",
    type=IdentityType(),
    help="Only accept invitations for a specific identity",
)
@LoginManager.requires_login(LoginManager.GROUPS_RS)
def invite_accept(
    *, group_id: uuid.UUID, identity: ParsedIdentity | None, login_manager: LoginManager
):
    """
    Accept an invitation to a group

    By default, all invitations to the group are accepted. To restrict this action to
    only specific invitations when there are multiple, use the `--identity` flag.
    """
    auth_client = login_manager.get_auth_client()
    groups_client = login_manager.get_groups_client()

    actions = build_invite_actions(
        auth_client, groups_client, "accept", group_id, identity
    )
    response = groups_client.batch_membership_action(group_id, actions)
    # if this failed to return at least one accepted user, figure out an error to show
    if not response.get("accept", None):
        try:
            raise ValueError(response["errors"]["accept"][0]["detail"])
        except LookupError:
            raise ValueError("Could not accept invite")

    formatted_print(response, text_format=get_invite_formatter("accept"))
