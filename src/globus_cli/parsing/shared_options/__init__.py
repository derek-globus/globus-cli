from __future__ import annotations

import functools
import typing as t

import click

from globus_cli.parsing.command_state import (
    debug_option,
    format_option,
    map_http_status_option,
    verbose_option,
)

C = t.TypeVar("C", bound=t.Union[t.Callable, click.Command])


def common_options(
    f: t.Callable | None = None, *, disable_options: list[str] | None = None
) -> t.Callable:
    """
    This is a multi-purpose decorator for applying a "base" set of options
    shared by all commands.
    It can be applied either directly, or given keyword arguments.

    Usage:

    >>> @common_options
    >>> def mycommand(abc, xyz):
    >>>     ...

    or

    >>> @common_options(disable_options=["format"])
    >>> def mycommand(abc, xyz):
    >>>     ...

    to disable use of `--format`
    """
    if disable_options is None:
        disable_options = []
    if f is None:
        return functools.partial(common_options, disable_options=disable_options)

    f = debug_option(f)
    f = verbose_option(f)
    f = click.help_option("-h", "--help")(f)

    # if the format option is being allowed, it needs to be applied to `f`
    if "format" not in disable_options:
        f = format_option(f)

    # if the --map-http-status option is being allowed, ...
    if "map_http_status" not in disable_options:
        f = map_http_status_option(f)

    return f


def collection_id_arg(f: t.Callable | None = None, *, metavar: str = "COLLECTION_ID"):
    if f is None:
        return functools.partial(collection_id_arg, metavar=metavar)
    return click.argument("collection_id", metavar=metavar, type=click.UUID)(f)


def endpoint_id_arg(f: t.Callable | None = None, *, metavar: str = "ENDPOINT_ID"):
    """
    This is the `ENDPOINT_ID` argument consumed by many Transfer endpoint
    related operations. It accepts alternate metavars for cases when another
    name is desirable (e.x. `SHARE_ID`, `HOST_ENDPOINT_ID`), but can also be
    applied as a direct decorator if no specialized metavar is being passed.

    Usage:

    >>> @endpoint_id_arg
    >>> def command_func(endpoint_id):
    >>>     ...

    or

    >>> @endpoint_id_arg(metavar='HOST_ENDPOINT_ID')
    >>> def command_func(endpoint_id):
    >>>     ...
    """
    if f is None:
        return functools.partial(endpoint_id_arg, metavar=metavar)
    return click.argument("endpoint_id", metavar=metavar, type=click.UUID)(f)


def task_notify_option(f: C) -> C:
    def notify_opt_callback(ctx, param, value):
        """
        Parse --notify
        - "" is the same as "off"
        - parse by lowercase, comma-split, strip spaces
        - "off,x" is invalid for any x
        - "on,x" is valid for any valid x (other than "off")
        - "failed", "succeeded", "inactive" are normal vals

        In code, produces True, False, or a set
        """
        # if no value was set, don't set any explicit options
        # the API default is "everything on"
        if value is None:
            return {}

        value = value.lower()
        value = [x.strip() for x in value.split(",")]
        # [""] is what you'll get if value is "" to start with
        # special-case it into "off", which helps avoid surprising scripts
        # which take a notification settings as inputs and build --notify
        if value == [""]:
            value = ["off"]

        off = "off" in value
        on = "on" in value
        # set-ize it -- duplicates are fine
        vals = {x for x in value if x not in ("off", "on")}

        if (vals or on) and off:
            raise click.UsageError('--notify cannot accept "off" and another value')

        allowed_vals = {"on", "succeeded", "failed", "inactive"}
        if not vals <= allowed_vals:
            raise click.UsageError(
                "--notify received at least one invalid value among {}".format(
                    list(vals)
                )
            )

        # return the notification options to send!
        # on means don't set anything (default)
        if on:
            return {}
        # off means turn off everything
        if off:
            return {
                "notify_on_succeeded": False,
                "notify_on_failed": False,
                "notify_on_inactive": False,
            }
        # otherwise, return the exact set of values seen
        else:
            return {
                "notify_on_succeeded": "succeeded" in vals,
                "notify_on_failed": "failed" in vals,
                "notify_on_inactive": "inactive" in vals,
            }

    return click.option(
        "--notify",
        callback=notify_opt_callback,
        help=(
            "Comma separated list of task events which notify by email. "
            "'on' and 'off' may be used to enable or disable notifications "
            "for all event types. Otherwise, use 'succeeded', 'failed', or "
            "'inactive'"
        ),
    )(f)


def task_submission_options(f):
    """
    Options shared by both transfer and delete task submission
    """

    def format_deadline_callback(ctx, param, value):
        if not value:
            return None
        return value.strftime("%Y-%m-%d %H:%M:%S")

    f = click.option(
        "--dry-run",
        is_flag=True,
        help="Don't actually submit the task, print submission data instead",
    )(f)
    f = task_notify_option(f)
    f = click.option(
        "--submission-id",
        help=(
            "Task submission ID, as generated by `globus task "
            "generate-submission-id`. Used for safe resubmission in the "
            "presence of network failures."
        ),
    )(f)
    f = click.option("--label", default=None, help="Set a label for this task.")(f)
    f = click.option(
        "--deadline",
        default=None,
        type=click.DateTime(),
        callback=format_deadline_callback,
        help="Set a deadline for this to be canceled if not completed by.",
    )(f)
    f = click.option(
        "--skip-activation-check",
        is_flag=True,
        help="Submit the task even if the endpoint(s) aren't currently activated.",
    )(f)

    return f


def delete_and_rm_options(
    f: t.Callable | None = None,
    *,
    supports_batch: bool = True,
    default_enable_globs: bool = False,
):
    """
    Options which apply both to `globus delete` and `globus rm`
    """
    if f is None:
        return functools.partial(
            delete_and_rm_options,
            supports_batch=supports_batch,
            default_enable_globs=default_enable_globs,
        )
    f = click.option("--recursive", "-r", is_flag=True, help="Recursively delete dirs")(
        f
    )
    f = click.option(
        "--ignore-missing",
        "-f",
        is_flag=True,
        help="Don't throw errors if the file or dir is absent",
    )(f)
    f = click.option(
        "--star-silent",
        "--unsafe",
        "star_silent",
        is_flag=True,
        help=(
            'Don\'t prompt when the trailing character is a "*".'
            + (" Implicit in --batch" if supports_batch else "")
        ),
    )(f)
    f = click.option(
        "--enable-globs/--no-enable-globs",
        is_flag=True,
        default=default_enable_globs,
        show_default=True,
        help=(
            "Enable expansion of *, ?, and [ ] characters in the last "
            "component of file paths, unless they are escaped with "
            "a preceeding backslash, \\"
        ),
    )(f)
    if supports_batch:
        f = click.option(
            "--batch",
            type=click.File("r"),
            help=(
                "Accept a batch of source/dest path pairs from a file. Use the "
                "special `-` value to read from stdin; otherwise opens the file from "
                "the argument and passes through lines from that file. Uses "
                "SOURCE_ENDPOINT_ID and DEST_ENDPOINT_ID as passed on the commandline. "
                "Commandline paths are still allowed and are used as prefixes to the "
                "batchmode inputs. "
            ),
        )(f)
    return f


def synchronous_task_wait_options(f):
    def polling_interval_callback(ctx, param, value):
        if not value:
            return None

        if value < 1:
            raise click.UsageError(
                f"--polling-interval={value} was less than minimum of 1"
            )

        return value

    def exit_code_callback(ctx, param, value):
        if not value:
            return None

        exit_stat_set = [0, 1] + list(range(50, 100))
        if value not in exit_stat_set:
            raise click.UsageError("--timeout-exit-code must have a value in 0,1,50-99")

        return value

    f = click.option(
        "--timeout",
        type=int,
        metavar="N",
        help=(
            "Wait N seconds. If the Task does not terminate by "
            "then, or terminates with an unsuccessful status, "
            "exit with status 1"
        ),
    )(f)
    f = click.option(
        "--polling-interval",
        default=1,
        type=int,
        show_default=True,
        callback=polling_interval_callback,
        help="Number of seconds between Task status checks.",
    )(f)
    f = click.option(
        "--heartbeat",
        "-H",
        is_flag=True,
        help=(
            'Every polling interval, print "." to stdout to '
            "indicate that task wait is still active"
        ),
    )(f)
    f = click.option(
        "--timeout-exit-code",
        type=int,
        default=1,
        show_default=True,
        callback=exit_code_callback,
        help=(
            "If the task times out, exit with this status code. Must have "
            "a value in 0,1,50-99"
        ),
    )(f)
    f = click.option("--meow", is_flag=True, hidden=True)(f)
    return f


def security_principal_opts(
    *,
    allow_anonymous=False,
    allow_all_authenticated=False,
    allow_provision=False,
):
    def preprocess_security_principals(f):
        @functools.wraps(f)
        def decorator(*args, **kwargs):
            identity = kwargs.pop("identity", None)
            group = kwargs.pop("group", None)
            provision_identity = kwargs.pop("provision_identity", None)

            has_identity = identity or provision_identity

            if identity and provision_identity:
                raise click.UsageError(
                    "Only one of --identity or --provision-identity allowed"
                )
            if kwargs.get("principal") is not None:
                if has_identity or group:
                    raise click.UsageError("You may only pass one security principal")
            else:
                if has_identity and group:
                    raise click.UsageError(
                        "You have passed both an identity and a group. "
                        "Please only pass one principal type"
                    )
                elif not has_identity and not group:
                    raise click.UsageError(
                        "You must provide at least one principal "
                        "(identity, group, etc.)"
                    )

                if identity:
                    kwargs["principal"] = ("identity", identity)
                elif provision_identity:
                    kwargs["principal"] = ("provision-identity", provision_identity)
                else:
                    kwargs["principal"] = ("group", group)

            return f(*args, **kwargs)

        return decorator

    def decorate(f: t.Callable) -> t.Callable:
        # order matters here -- the preprocessor must run after option
        # application, so it has to be applied first
        if isinstance(f, click.Command):
            # if we're decorating a command, put the preprocessor on its
            # callback, not on `f` itself
            f.callback = preprocess_security_principals(f.callback)
        else:
            # otherwise, we're applying to a function, but other decorators may
            # have been applied to give it params
            # so, copy __click_params__ to preserve those parameters
            oldfun = f
            f = preprocess_security_principals(f)
            f.__click_params__ = getattr(oldfun, "__click_params__", [])  # type: ignore

        f = click.option(
            "--identity",
            metavar="IDENTITY_ID_OR_NAME",
            help="Identity to use as a security principal",
        )(f)
        f = click.option(
            "--group", metavar="GROUP_ID", help="Group to use as a security principal"
        )(f)

        if allow_anonymous:
            f = click.option(
                "--anonymous",
                "principal",
                flag_value=("anonymous", ""),
                help="Allow anyone access, even without logging in "
                "(treated as a security principal)",
            )(f)
        if allow_all_authenticated:
            f = click.option(
                "--all-authenticated",
                "principal",
                flag_value=("all_authenticated_users", ""),
                help="Allow anyone access, as long as they login "
                "(treated as a security principal)",
            )(f)

        if allow_provision:
            f = click.option(
                "--provision-identity",
                metavar="IDENTITY_USERNAME",
                help="Identity username to use as a security principal. "
                "Identity will be provisioned if it does not exist.",
            )(f)

        return f

    return decorate


def no_local_server_option(f):
    """
    Option for commands that start auth flows and might need to disable
    the default local server behavior
    """
    return click.option(
        "--no-local-server",
        is_flag=True,
        help=(
            "Manual authorization by copying and pasting an auth code. "
            "This option is implied if the CLI detects you are using a "
            "remote connection."
        ),
    )(f)
