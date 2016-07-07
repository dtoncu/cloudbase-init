# Copyright 2016 Cloudbase Solutions Srl
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

from oslo_log import log as oslo_logging

import json
import requests

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.metadata.services import base
from cloudbaseinit.utils import encoding

CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class PacketService(base.BaseHTTPMetadataService):

    """Metadata Service for Packet.

    Packet is a NYC-based infrastructure startup, focused on reinventing
    how SaaS/PaaS companies go global with premium bare metal and container
    hosting.
    """

    def __init__(self):
        super(PacketService, self).__init__(
            base_url=CONF.packet.metadata_base_url,
            https_allow_insecure=CONF.packet.https_allow_insecure,
            https_ca_bundle=CONF.packet.https_ca_bundle)
        self._raw_data = {}
        self._enable_retry = True

    def _get_data(self, path):
        """Obtain the required information from the metadata provider.

        The path should follow the following template:
        `[metadata|userdata](/key_name)+`

        .. note::

            Some examples:
                * `metadata/hostname`
                * `metadata/operating_system/distro`
                * `metadata/network/interfaces`
                * `metadata/ssh_keys`
                * `metadata/ssh_keys/0`

            If the value for the required key is not a string type
            it will be returned the number of items from that
            container.
        """
        current_container = self._raw_data
        containers = [container for container in path.split("/")
                      if container != '']
        if not containers:
            raise base.NotExistingMetadataException()

        while containers:
            try:
                container_name = containers.pop(0)
                if container_name.isdigit():
                    container_name = int(container_name)
                current_container = current_container[container_name]
            except (KeyError, IndexError):
                LOG.debug("The container %r does not exists into %r",
                          container_name, current_container)
                break
        else:
            if isinstance(current_container, (tuple, list, dict)):
                return len(current_container)
            else:
                return current_container

        raise base.NotExistingMetadataException()

    def load(self):
        """Load all the available information from the metadata service."""
        super(PacketService, self).load()
        for path in ("metadata", "userdata"):
            url = requests.compat.urljoin(self._base_url, path)
            try:
                action = lambda: self._http_request(url)
                self._raw_data[path] = self._exec_with_retry(action)
            except requests.RequestException as exc:
                LOG.debug("%(data)s not found at URL %(url)r: %(reason)r",
                          {"data": path.title(), "url": url, "reason": exc})
                return False
        try:
            self._raw_data["metadata"] = json.loads(encoding.get_as_string(
                self._raw_data["metadata"]))
        except ValueError as exc:
            LOG.warning("Failed to load metadata: %s", exc)
            return False

        return True

    def get_instance_id(self):
        """Get the identifier for the current instance.

        The instance identifier provides an unique way to address an
        instance into the current metadata provider.
        """
        return self._get_cache_data('metadata/id', decode=True)

    def get_host_name(self):
        """Get the hostname for the current instance.

        The hostname is the label assigned to the current instance used to
        identify it in various forms of electronic communication.
        """
        return self._get_cache_data('metadata/hostname', decode=True)

    def get_public_keys(self):
        """Get a list of space-stripped strings as public keys."""
        keys = []
        keys_number = self._get_cache_data("metadata/ssh_keys", decode=False)
        for index in range(keys_number):
            path = "metadata/ssh_keys/{index}".format(index=index)
            keys.append(self._get_cache_data(path, decode=True))

        return keys if keys else None

    def get_user_data(self):
        """Get the available user data for the current instance."""
        return self._get_cache_data("userdata", decode=False)
