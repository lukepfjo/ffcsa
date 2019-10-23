#!/usr/bin/env bash

function git-merge-subpath() {
    if [[ $1 == "--no-squash" ]]; then
        local NOSQUASH=1
        shift
    fi
    if (( $# != 3 )); then
        PARAMS="[--no-squash] SOURCE_COMMIT SOURCE_PREFIX DEST_PREFIX"
        echo "USAGE: ${FUNCNAME[0]} $PARAMS"
        exit 1
    fi

    # Friendly parameter names; strip any trailing slashes from prefixes.
    local SOURCE_COMMIT="$1" SOURCE_PREFIX="${2%/}" DEST_PREFIX="${3%/}"

	IFS='/'
	read -ra SPLIT <<< "$SOURCE_COMMIT"
	IFS=' '
	SOURCE_REMOTE="${SPLIT[0]}"
	SOURCE_REMOTE_URL=$(git remote -v | grep "$SOURCE_REMOTE\t.*(fetch)" | cut -f2 | cut -f1 -d ' ')

    local SOURCE_SHA1=$(git rev-parse --verify "$SOURCE_COMMIT^{commit}") || exit 1

    local OLD_SHA1
    local GIT_ROOT=$(git rev-parse --show-toplevel)
    if [[ -n "$(ls -A "$GIT_ROOT/$DEST_PREFIX" 2> /dev/null)" ]]; then
        # OLD_SHA1 will remain empty if there is no match.
        RE="^${FUNCNAME[0]}: [0-9a-f]{40} $SOURCE_PREFIX $DEST_PREFIX\$"
        OLD_SHA1=$(git log -1 --format=%b -E --grep="$RE" \
                   | grep --color=never -E "$RE" | tail -1 | awk '{print $2}')
    fi

    local OLD_TREEISH
    if [[ -n $OLD_SHA1 ]]; then
        OLD_TREEISH="$OLD_SHA1:$SOURCE_PREFIX"
    else
        # This is the first time git-merge-subpath is run, so diff against the
        # empty commit instead of the last commit created by git-merge-subpath.
        OLD_TREEISH=$(git hash-object -t tree /dev/null)
    fi &&

    if [[ $NOSQUASH ]]; then
        git merge -s ours --allow-unrelated-histories --no-commit "$SOURCE_COMMIT"
    fi &&

    local DIFF=$(git diff --color=never "$OLD_TREEISH" "$SOURCE_COMMIT:$SOURCE_PREFIX")
    if [[ -n $DIFF ]]; then
        echo $DIFF | git apply -3 --directory="$DEST_PREFIX" || git mergetool
    fi

    if (( $? == 1 )); then
        echo "Uh-oh! Try cleaning up with |git reset --merge|."
    else
        git commit -em "Merge $SOURCE_REMOTE:$SOURCE_PREFIX/ to $DEST_PREFIX/

Remote tracking url: $SOURCE_REMOTE_URL

# Feel free to edit the title and body above, but make sure to keep the
# ${FUNCNAME[0]}: line below intact, so ${FUNCNAME[0]} can find it
# again when grepping git log.
${FUNCNAME[0]}: $SOURCE_SHA1 $SOURCE_PREFIX $DEST_PREFIX"
    fi
}

git-merge-subpath $@
