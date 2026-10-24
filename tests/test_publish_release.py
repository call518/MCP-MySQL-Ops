"""Release publication tests without Git writes or external requests."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import publish_release as release


@pytest.mark.parametrize("previous", [None, "v1.0.0"])
def test_release_notes_include_full_messages(previous):
    sha = "a" * 40
    message = "Fix query\n\nDetails with ``` and $(echo unsafe)."
    with patch.object(
        release, "command", side_effect=[sha] + (
            ["b" * 40, ""] if previous else []
        ) + [f"{sha}\0{message}\0"]
    ) as command:
        notes = release.release_notes("owner/repo", "v1.1.0", previous)
    assert message in notes
    assert "````text" in notes
    assert f"/commit/{sha}" in notes
    assert ("Full Changelog" in notes) == bool(previous)
    if previous:
        assert command.call_args_list[2].args[:3] == (
            "git", "merge-base", "--is-ancestor"
        )


@pytest.mark.parametrize("tag", ["v1.1.0", "v1.1.0rc1"])
def test_publish_uses_latest_published_release_and_notes_file(tag):
    sha = "a" * 40
    releases = [
        {"tag_name": "v0.9.0", "draft": False, "published_at": "2026-01-01"},
        {"tag_name": "v1.0.0", "draft": False, "published_at": "2026-02-01"},
        {"tag_name": "v2.0.0", "draft": True, "published_at": None},
    ]

    def command(*args):
        if args[:3] == ("gh", "release", "create"):
            assert args[3] == tag
            assert Path(args[args.index("--notes-file") + 1]).read_text() == "notes"
            assert ("--prerelease" in args) == tag.endswith("rc1")
            return ""
        if args[:2] == ("gh", "api") and "--paginate" in args:
            return json.dumps([releases])
        return sha

    with patch.object(release, "command", side_effect=command) as commands:
        with patch.object(release, "release_notes", return_value="notes") as notes:
            release.publish_release("owner/repo", tag)
    notes.assert_called_once_with("owner/repo", tag, "v1.0.0")
    assert commands.call_args.args[:3] == ("gh", "release", "create")


@pytest.mark.parametrize("draft", [False, True])
def test_existing_release_is_never_overwritten(draft):
    sha = "a" * 40
    pages = [[{"tag_name": "v1.0.0", "draft": draft}]]
    with patch.object(
        release, "command", side_effect=[sha, sha, sha, json.dumps(pages)]
    ) as command:
        if draft:
            with pytest.raises(ValueError, match="draft"):
                release.publish_release("owner/repo", "v1.0.0")
        else:
            release.publish_release("owner/repo", "v1.0.0")
    assert command.call_count == 4


def test_moved_tag_blocks_release():
    with patch.object(release, "command", side_effect=["local", "remote"]):
        with pytest.raises(ValueError, match="must match"):
            release.publish_release("owner/repo", "v1.0.0")
