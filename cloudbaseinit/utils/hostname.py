# Copyright 2015 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import platform
import re

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit import exception

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)

NETBIOS_HOST_NAME_MAX_LEN = 15


def _cannot_be_set(osutils):
    """Determine if the hostname can be set or not.

    Information about this can be found at the following link:
    https://msdn.microsoft.com/en-us/library/windows/hardware/dn922649(v=vs.85).aspx
    """
    return osutils.check_os_version(10, 0) and osutils.is_in_unattended()


def set_hostname(osutils, hostname):
    """Change the hostname for the underlying platform.

    If netbios_host_name_compatibility is set to True in the configuration
    file, then the hostname is truncated to NETBIOS_HOST_NAME_MAX_LEN.

    Params:
        osutils: instance of osutils
        hostname: the desired hostname

    Returns:
        (new_hostname, reboot_required)
        new_hostname: the possibly truncated hostname
        reboot_required: True if the hostname was changed and a reboot is
            required, False otherwise.

    """
    if _cannot_be_set(osutils):
        raise exception.WindowsCloudbaseInitException(
            "The hostname can not be set in the unattended phase "
            "for this instance.")

    hostname = hostname.split('.', 1)[0]
    if (len(hostname) > NETBIOS_HOST_NAME_MAX_LEN and
            CONF.netbios_host_name_compatibility):
            LOG.warn('Truncating host name for Netbios compatibility. '
                     'Old name: %(old_hostname)s, new name: '
                     '%(new_hostname)s' %
                     {'old_hostname': hostname,
                      'new_hostname': hostname[:NETBIOS_HOST_NAME_MAX_LEN]})
            hostname = hostname[:NETBIOS_HOST_NAME_MAX_LEN]
    hostname = re.sub(r'-$', '0', hostname)
    if platform.node().lower() == hostname.lower():
        LOG.debug("Hostname already set to: %s" % hostname)
        reboot_required = False
    else:
        LOG.info("Setting hostname: %s" % hostname)
        reboot_required = osutils.set_host_name(hostname)

    return hostname, reboot_required
