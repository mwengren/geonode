# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2012 OpenPlans
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
from django.conf import settings

if not hasattr(settings, 'OGC_SERVER'):
    msg = (
        'Please configure OGC_SERVER when enabling geonode.geoserver.'
        ' More info can be found at '
        'http://docs.geonode.org/en/master/reference/developers/settings.html#ogc-server')
    raise ImproperlyConfigured(msg)

class ServerDoesNotExist(Exception):
    pass


class OGC_Server(object):

    """
    OGC Server object.
    """

    def __init__(self, ogc_server, alias):
        self.alias = alias
        self.server = ogc_server

    def __getattr__(self, item):
        return self.server.get(item)

    @property
    def credentials(self):
        """
        Returns a tuple of the server's credentials.
        """
        creds = namedtuple('OGC_SERVER_CREDENTIALS', ['username', 'password'])
        return creds(username=self.USER, password=self.PASSWORD)

    @property
    def datastore_db(self):
        """
        Returns the server's datastore dict or None.
        """
        if self.DATASTORE and settings.DATABASES.get(self.DATASTORE, None):
            return settings.DATABASES.get(self.DATASTORE, dict())
        else:
            return dict()

    @property
    def ows(self):
        """
        The Open Web Service url for the server.
        """
        location = self.PUBLIC_LOCATION if self.PUBLIC_LOCATION else self.LOCATION
        return self.OWS_LOCATION if self.OWS_LOCATION else location + 'ows'

    @property
    def rest(self):
        """
        The REST endpoint for the server.
        """
        return self.LOCATION + \
            'rest' if not self.REST_LOCATION else self.REST_LOCATION

    @property
    def public_url(self):
        """
        The global public endpoint for the server.
        """
        return self.LOCATION if not self.PUBLIC_LOCATION else self.PUBLIC_LOCATION

    @property
    def internal_ows(self):
        """
        The Open Web Service url for the server used by GeoNode internally.
        """
        location = self.LOCATION
        return location + 'ows'

    @property
    def internal_rest(self):
        """
        The internal REST endpoint for the server.
        """
        return self.LOCATION + 'rest'

    @property
    def hostname(self):
        return urlsplit(self.LOCATION).hostname

    @property
    def netloc(self):
        return urlsplit(self.LOCATION).netloc

    def __str__(self):
        return self.alias


class OGC_Servers_Handler(object):

    """
    OGC Server Settings Convenience dict.
    """

    def __init__(self, ogc_server_dict):
        self.servers = ogc_server_dict
        # FIXME(Ariel): Are there better ways to do this without involving
        # local?
        self._servers = local()

    def ensure_valid_configuration(self, alias):
        """
        Ensures the settings are valid.
        """
        try:
            server = self.servers[alias]
        except KeyError:
            raise ServerDoesNotExist("The server %s doesn't exist" % alias)

        datastore = server.get('DATASTORE')
        uploader_backend = getattr(
            settings,
            'UPLOADER',
            dict()).get(
            'BACKEND',
            'geonode.rest')

        if uploader_backend == 'geonode.importer' and datastore and not settings.DATABASES.get(
                datastore):
            raise ImproperlyConfigured(
                'The OGC_SERVER setting specifies a datastore '
                'but no connection parameters are present.')

        if uploader_backend == 'geonode.importer' and not datastore:
            raise ImproperlyConfigured(
                'The UPLOADER BACKEND is set to geonode.importer but no DATASTORE is specified.')

        if 'PRINTNG_ENABLED' in server:
            raise ImproperlyConfigured("The PRINTNG_ENABLED setting has been removed, use 'PRINT_NG_ENABLED' instead.")

    def ensure_defaults(self, alias):
        """
        Puts the defaults into the settings dictionary for a given connection where no settings is provided.
        """
        try:
            server = self.servers[alias]
        except KeyError:
            raise ServerDoesNotExist("The server %s doesn't exist" % alias)

        server.setdefault('BACKEND', 'geonode.geoserver')
        server.setdefault('LOCATION', 'http://localhost:8080/geoserver/')
        server.setdefault('USER', 'admin')
        server.setdefault('PASSWORD', 'geoserver')
        server.setdefault('DATASTORE', str())
        server.setdefault('GEOGIT_DATASTORE_DIR', str())

        for option in ['MAPFISH_PRINT_ENABLED', 'PRINT_NG_ENABLED', 'GEONODE_SECURITY_ENABLED',
                       'BACKEND_WRITE_ENABLED']:
            server.setdefault(option, True)

        for option in ['GEOGIT_ENABLED', 'WMST_ENABLED', 'WPS_ENABLED']:
            server.setdefault(option, False)

    def __getitem__(self, alias):
        if hasattr(self._servers, alias):
            return getattr(self._servers, alias)

        self.ensure_defaults(alias)
        self.ensure_valid_configuration(alias)
        server = self.servers[alias]
        server = OGC_Server(alias=alias, ogc_server=server)
        setattr(self._servers, alias, server)
        return server

    def __setitem__(self, key, value):
        setattr(self._servers, key, value)

    def __iter__(self):
        return iter(self.servers)

    def all(self):
        return [self[alias] for alias in self]