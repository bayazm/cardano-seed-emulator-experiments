#!/usr/bin/env bash
set -euo pipefail

candidate=10.154.0.71
owner=b14-relay-admission
installed=/cardano/relay-admission.sh
chains=(INPUT OUTPUT)
incumbents=(150 151 152 153)

error() { printf '%s\n' "$*" >&2; }

check_address() {
    local asn=$1 addresses
    shift
    addresses=$("$@" ip -o -4 addr show scope global) || return 1
    awk -v expected="10.$asn.0.71" '
        { split($4, address, "/"); if (address[1] == expected) found++ }
        END { exit found != 1 }
    ' <<< "$addresses"
}

rule_args() {
    local chain=$1 verdict=$2
    args=(-s "$candidate/32")
    if [[ $chain == OUTPUT ]]; then args=(-d "$candidate/32"); fi
    args+=(-p tcp -m tcp --dport 3001 -m comment --comment "$owner" -j "$verdict")
}

read_chain() {
    local chain=$1 listing line
    listing=$(iptables -w -S "$chain") || return 1
    rules=()
    while IFS= read -r line; do
        if [[ $line == "-A $chain "* ]]; then
            rules+=("${line//\"$owner\"/$owner}")
        fi
    done <<< "$listing"
}

expected_chain() {
    local chain=$1 state=$2 drop accept
    rule_args "$chain" DROP
    drop="-A $chain ${args[*]}"
    rule_args "$chain" ACCEPT
    accept="-A $chain ${args[*]}"
    read_chain "$chain" || return 1
    local owned=() rule
    for rule in "${rules[@]}"; do
        if [[ " $rule " == *" --comment $owner "* ]]; then owned+=("$rule"); fi
    done
    if [[ $state == granted ]]; then
        [[ ${#owned[@]} == 2 && ${rules[0]-} == "$accept" && ${rules[1]-} == "$drop" ]]
    else
        [[ ${#owned[@]} == 1 && ${rules[0]-} == "$drop" ]]
    fi
}

node_state() {
    local state
    for state in denied granted; do
        if expected_chain INPUT "$state" && expected_chain OUTPUT "$state"; then
            printf '%s\n' "$state"
            return
        fi
    done
    printf '%s\n' inconsistent
    return 1
}

deny_chain() {
    local chain=$1 rule drop accept position found=0
    rule_args "$chain" DROP
    drop="-A $chain ${args[*]}"
    rule_args "$chain" ACCEPT
    accept="-A $chain ${args[*]}"
    read_chain "$chain" || return 1

    for rule in "${rules[@]}"; do
        if [[ $rule == "$drop" ]]; then found=1; fi
    done
    # Install a missing DROP before removing any exception.
    local failed=0
    if (( ! found )); then
        rule_args "$chain" DROP
        iptables -w -I "$chain" 1 "${args[@]}" || failed=1
    fi
    rule_args "$chain" ACCEPT
    for rule in "${rules[@]}"; do
        if [[ $rule == "$accept" ]]; then
            iptables -w -D "$chain" "${args[@]}" || failed=1
        fi
    done

    read_chain "$chain" || return 1
    if [[ ${rules[0]-} != "$drop" ]]; then
        error "$chain: B14 DROP is not first; cannot safely restore rule ordering"
        return 1
    fi
    # Keep rule 1 effective. Delete only matching duplicates, from the end
    # so that earlier positions and the order of foreign rules stay intact.
    for (( position=${#rules[@]}; position > 1; position-- )); do
        if [[ ${rules[position-1]} == "$drop" ]]; then
            iptables -w -D "$chain" "$position" || failed=1
        fi
    done
    expected_chain "$chain" denied || failed=1
    return "$failed"
}

deny_node() {
    local chain failed=0
    for chain in "${chains[@]}"; do
        deny_chain "$chain" || { error "$chain: could not verify B14 denial"; failed=1; }
    done
    return "$failed"
}

inside() {
    local action=$1 asn=$2 chain
    [[ -f /.dockerenv && -f $installed && $asn =~ ^15[0-3]$ ]] || return 1
    check_address "$asn" || { error "Unexpected address on AS$asn"; return 1; }
    case $action in
        deny) deny_node ;;
        grant)
            [[ $asn == 153 ]] || return 1
            for chain in "${chains[@]}"; do
                if expected_chain "$chain" granted; then continue; fi
                expected_chain "$chain" denied || return 1
                rule_args "$chain" ACCEPT
                iptables -w -I "$chain" 1 "${args[@]}" || return 1
                expected_chain "$chain" granted || return 1
            done
            ;;
        state) node_state ;;
        status)
            local failed=0
            node_state || failed=1
            for chain in "${chains[@]}"; do
                iptables -w -nvL "$chain" --line-numbers || failed=1
            done
            return "$failed"
            ;;
        *) return 2 ;;
    esac
}

if [[ $0 == "$installed" && ${1:-} == --inside && $# == 3 ]]; then
    inside "$2" "$3"
    exit
fi

if [[ $# != 1 || ! ${1:-} =~ ^(status|deny|grant|revoke|restore)$ ]]; then
    error "Usage: relay-admission.sh {status|deny|grant|revoke|restore}"
    exit 2
fi

action=$1
: "${COMPOSE_PROJECT_NAME:?Set COMPOSE_PROJECT_NAME to the B14 project}"
[[ $COMPOSE_PROJECT_NAME =~ ^[a-z0-9][a-z0-9_-]*$ ]] || exit 2
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../output"
compose=(docker-compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml)
# Serialize controllers using this generated output directory.
exec 9>.b14-firewall.lock
flock -x 9

declare -A ids
resolve() {
    local asn=$1 service="hnode_${1}_host_0" id labels mode
    id=$("${compose[@]}" ps -q "$service") || return 1
    [[ $id =~ ^[0-9a-f]{12,64}$ ]] || return 1
    labels=$(docker inspect --format '{{.HostConfig.NetworkMode}} {{.State.Running}} {{index .Config.Labels "com.docker.compose.project"}} {{index .Config.Labels "com.docker.compose.service"}} {{index .Config.Labels "org.seedsecuritylabs.seedemu.meta.experiment"}}' "$id") || return 1
    mode=${labels%% *}
    [[ -n $mode && $mode != host && $mode != container:* ]] || return 1
    [[ ${labels#* } == "true $COMPOSE_PROJECT_NAME $service $owner" ]] || return 1
    docker exec "$id" test -f "$installed" || return 1
    check_address "$asn" docker exec "$id" || return 1
    ids[$asn]=$id
}

remote() {
    local asn=$1 operation=$2
    [[ -n ${ids[$asn]:-} ]] || return 1
    docker exec "${ids[$asn]}" bash "$installed" --inside "$operation" "$asn"
}

deny_all() {
    local asn failed=0
    # Remove the relay exception first even if another incumbent is unavailable.
    for asn in 153 150 151 152; do
        remote "$asn" deny || { error "AS$asn: denial could not be verified"; failed=1; }
    done
    return "$failed"
}

check_phase() {
    local relay_state=$1 asn expected actual
    for asn in "${incumbents[@]}"; do
        expected=denied
        if [[ $asn == 153 ]]; then expected=$relay_state; fi
        actual=$(remote "$asn" state) || return 1
        [[ $actual == "$expected" ]] || return 1
    done
}

failed=0
for asn in "${incumbents[@]}" 154; do
    resolve "$asn" || { error "AS$asn: could not validate the selected B14 container"; failed=1; }
done

case $action in
    status)
        for asn in "${incumbents[@]}"; do
            printf 'AS%s\n' "$asn"
            report=$(remote "$asn" status) || failed=1
            printf '%s\n' "$report"
            state=${report%%$'\n'*}
            if [[ $asn != 153 && $state != denied ]]; then failed=1; fi
        done
        if (( failed )); then
            error "B14 admission state could not be verified."
            exit 1
        fi
        printf 'B14 admission state: %s\n' "$state"
        ;;
    deny|revoke|restore)
        deny_all || failed=1
        (( ! failed )) || exit 1
        printf '%s\n' 'B14 baseline verified: candidate denied by AS150–AS153.'
        ;;
    grant)
        if (( ! failed )) && check_phase granted; then
            printf '%s\n' 'B14 admission already verified on AS153.'
            exit
        fi
        # Keep rollback armed throughout the grant and its verification.
        rollback() {
            local code=$?
            trap - EXIT
            error "Grant failed. Restoring B14 denial."
            deny_all || error "Rollback incomplete. Treat access as potentially granted and check AS153."
            exit "$code"
        }
        trap rollback EXIT
        trap 'exit 130' INT
        trap 'exit 143' TERM
        (( ! failed )) && deny_all && remote 153 grant && check_phase granted || exit 1
        trap - EXIT INT TERM
        printf '%s\n' 'B14 admission verified on AS153. AS150–AS152 continue to deny the candidate.'
        ;;
esac
