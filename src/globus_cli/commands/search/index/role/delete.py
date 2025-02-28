import uuid

import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import formatted_print

from ..._common import index_id_arg


@command("delete")
@index_id_arg
@click.argument("ROLE_ID")
@LoginManager.requires_login(LoginManager.SEARCH_RS)
def delete_command(
    *,
    index_id: uuid.UUID,
    role_id: str,
    login_manager: LoginManager,
):
    """Delete a role (requires admin or owner)"""
    search_client = login_manager.get_search_client()
    formatted_print(
        search_client.delete_role(index_id, role_id),
        simple_text=f"Successfully removed role {role_id} from index {index_id}",
    )
