#!/usr/bin/env python
import os
import sys
import time
import calendar
import glob

import subprocess


def _start_services(context, service_names, fatjar, release, wait, proxy):
    for service_name in service_names:
        start_one(context, service_name, fatjar, release, proxy)

    if wait:
        _wait_for_services(context, service_names, wait)


def start_one(context, service_name, fatjar, release, proxy, port=None):
    if release:
        run_from = "RELEASE"
    elif fatjar:
        run_from = "SNAPSHOT"
    else:
        run_from = "SOURCE"

    existing_service_status = context.get_service(service_name).status()

    if len(existing_service_status) > 0:
        print "There is already: '" + str(len(existing_service_status)) + "' instance(s) of the service: '" + service_name + "' running"
        return False

    if context.start_service(service_name, run_from, proxy, None, None, port):
        if context.get_service(service_name).is_started_on_default_port():
            print "Started: " + service_name
            return True

    return False


def stop_profile(context, profile):
    for service_name in context.application.services_for_profile(profile):
        context.kill(service_name)


def _now():
    return int(calendar.timegm(time.gmtime()))


def _wait_for_services(context, service_names, seconds_to_wait):

    waiting_for_services = []

    for service_name in service_names:
        if "healthcheck" in context.service_data(service_name):
            waiting_for_services += [context.get_service(service_name)]

    end_time = _now() + seconds_to_wait

    while waiting_for_services and _now() < end_time:

        services_to_check = list(waiting_for_services)

        for service in services_to_check:

            if _now() >= end_time:
                break

            if service.run_healthcheck:
                print "Service '%s' has started successfully" % service.service_name
                waiting_for_services.remove(service)
            else:
                seconds_remaining = end_time - _now()
                if seconds_remaining % 5 == 0 or seconds_remaining < 10:
                    print "Waiting for %s to start, %s second%s before timeout" % (service.service_name, seconds_remaining, "s" if seconds_to_wait != 1 else "")

        if waiting_for_services:
            time.sleep(1)

    if waiting_for_services:
        services_timed_out = []
        for service in waiting_for_services:
            services_timed_out += [service.service_name]
        print "Timed out starting service(s): %s" % ", ".join(services_timed_out)
        sys.exit(-1)
    else:
        print "All services passed healthcheck"


def clean_logs(context, service_name):
    data = context.service_data(service_name)
    if "location" in data:
        sources_logs = context.application.workspace + data["location"] + "/logs/*.log*"
        fatjar_logs = context.application.workspace + data["location"] + "/target/logs/*.log*"

        num_files = _remove_files_wildcard(sources_logs)
        num_files += _remove_files_wildcard(fatjar_logs)
        print "Removed %d log files in %s" % (num_files, service_name)


def _remove_files_wildcard(files):
    r = glob.glob(files)
    for i in r:
        os.remove(i)
    return len(r)


def overridden_port(services, port):
    if len(services) == 1 and port is not None:
        return port
    else:
        return None


def _get_running_process_args(context, service_name):

    service = context.get_service(service_name)

    pattern = service.get_pattern()

    if service.is_started_on_default_port():
#        command = "ps -eo args | egrep '%s' | egrep -v 'egrep %s' | awk '{{print  } }'" % (pattern, pattern)
        command = "wmic process where \"CommandLine like '%pattern%'\" get CommandLine"
        ps_command = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        ps_output = ps_command.stdout.read()

        if ps_output:
            return ps_output.split("\n")[:-1][0]

    return ""


def _get_git_rev(context, service_name):
    details = context.get_service(service_name).request_running_service_details_on_default_port()

    if details:
        return details.get("Git-Head-Rev", "")

    return ""


def display_info(context, service_name):
    arguments = _get_running_process_args(context, service_name)
    git_revision = _get_git_rev(context, service_name)
    print
    print "| %s" % service_name
    print "| %s" % arguments
    print "| %s" % git_revision
    comments = ""
    if git_revision == "":
        comments += "(No Details) "
    if arguments == "":
        comments += "(Not Running) "
    print "| " + comments
