#!/usr/bin/env python
import os
import signal
import sys
import time
import requests
import random
from jinja2 import Environment, FileSystemLoader

# supervisord xml-rpc connection
import xmlrpc.client
svd = xmlrpc.client.ServerProxy('http://127.0.0.1:9001/RPC2')
identity = os.environ.get('CONCIERGE_IDENTITY')
portier_host = os.environ.get('PORTIER_HOST', default="portier.chaoswest.tv")
portier_scheme = os.environ.get('PORTIER_SCHEME', default="https")
base_url = '%s://%s/concierge/api/%s' % (portier_scheme, portier_host, identity)

skills = [
    'restream'
]

edge_nodes = [
    'rtmp://ingest-nbg.chaoswest.tv:1936/',
    'rtmp://ingest-fsn.chaoswest.tv:1936/',
]

interval = 2

# runtime stuff
claims = []


def svd_update():
    try:
        r = svd.supervisor.reloadConfig()
    except xmlrpc.client.Fault as e:
        if e.faultCode == 6:  # SHUTDOWN_STATE
            print('svd shutting down')
            return
        else:
            raise

    added, changed, removed = r[0]

    for group in added:
        print('adding %s' % group)
        svd.supervisor.addProcessGroup(group)

    for group in changed:
        svd.supervisor.stopProcessGroup(group)
        svd.supervisor.removeProcessGroup(group)
        svd.supervisor.addProcessGroup(group)

    for group in removed:
        # we don't want to remove ourselves by accident ;)
        print('removing %s' % group)
        if group == 'concierge':
            print('wait, no! :D' % group)
            continue

        svd.supervisor.stopProcessGroup(group)
        svd.supervisor.removeProcessGroup(group)


def sigterm_handler(signum, frame):
    print("concierge shutting down.")
    # if concierge dies, all tasks need to be released!
    # supervisor has a eventlistener and will kill itself (and thus all running
    # tasks) if concierge dies.
    for claim in claims:
        release_task(claim.get('uuid'))
    sys.exit(0)


def template_tasks():
    j = Environment(loader=FileSystemLoader('tasks.templates'))
    for claim in claims:
        tpl = j.get_template('%s.conf.j2' % claim.get('type'))
        with open("/app/tasks.d/%s.conf" % claim.get('uuid'), "w") as f:
            f.write(tpl.render(edge=random.choice(edge_nodes), uuid=claim.get('uuid'), cfg=claim.get('configuration')))


def stop_task(uuid):
    global claims
    # remove from local claim list
    remaining_claims = [claim for claim in claims if claim.get('uuid') != uuid]
    claims = remaining_claims

    # remove task config
    file = '/app/tasks.d/%s.conf' % uuid
    try:
        os.remove(file)
    except:  # noqa
        print('error deleting task configfile', file)

    # reload supervisord config
    svd_update()


def release_task(uuid):
    global claims
    r = requests.post('%s/release/%s' % (base_url, uuid))

    if r.status_code != 200:
        return

    stop_task(uuid)


def claim_task(uuid):
    global claims
    r = requests.post('%s/claim/%s' % (base_url, uuid)).json()
    claims.append({
        'uuid': r.get('uuid'),
        'type': r.get('type'),
        'configuration': r.get('configuration')
    })

    # rewrite supervisord config files
    template_tasks()

    # reload supervisord config
    svd_update()


def loop():
    global claims
    while True:
        # portier heartbeat
        r = requests.post('%s/heartbeat' % base_url)
        resp = r.json()

        # compare local list of claims with portiers list of claims
        for pclaim in resp['claims']:

            # search for claims we don't know of
            known_claim = ['x' for claim in claims if claim.get('uuid') == pclaim.get('uuid')]
            if not known_claim:
                # portier thinks we claimed a task, but we don't know this claim.
                # we need to release the task, so it can again be picked up.
                print('releasing %s' % pclaim.get('uuid'))
                release_task(pclaim.get('uuid'))

        for claim in claims:
            # search for claims that portier doesn't know of (maybe taken away on purpose)
            known_claim = ['x' for pclaim in resp['claims'] if claim.get('uuid') == pclaim.get('uuid')]
            if not known_claim:
                print('stopping %s' % claim.get('uuid'))
                stop_task(claim.get('uuid'))

        # search for new available tasks that we can handle and try to claim one.
        for task in resp['available']:
            if task.get('type') in skills:
                claim_task(task.get('uuid'))
                break

        time.sleep(interval)


def main():
    # program setup
    signal.signal(signal.SIGTERM, sigterm_handler)

    # check connection to supervisord
    loop()


main()
