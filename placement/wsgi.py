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
"""WSGI script for Placement API

WSGI handler for running Placement API under Apache2, nginx, gunicorn etc.
"""

import logging as py_logging
import os
import os.path

from oslo_log import log as logging
from oslo_service import _options as service_opts
from oslo_utils import importutils
import pbr.version

from placement import db_api
from placement import deploy
from nova.common import config
from nova import conf


profiler = importutils.try_import('osprofiler.opts')


CONFIG_FILE = 'nova.conf'


version_info = pbr.version.VersionInfo('nova')


def setup_logging(config):
    # Any dependent libraries that have unhelp debug levels should be
    # pinned to a higher default.
    extra_log_level_defaults = [
        'routes=INFO',
    ]
    logging.set_defaults(default_log_levels=logging.get_default_log_levels() +
                    extra_log_level_defaults)
    logging.setup(config, 'nova')
    py_logging.captureWarnings(True)


def _get_config_file(env=None):
    if env is None:
        env = os.environ

    dirname = env.get('OS_PLACEMENT_CONFIG_DIR', '/etc/nova').strip()
    return os.path.join(dirname, CONFIG_FILE)


def _parse_args(argv, default_config_files):
    logging.register_options(conf.CONF)

    if profiler:
        profiler.set_defaults(conf.CONF)

    config.set_middleware_defaults()

    conf.CONF(argv[1:], project='nova', version=version_info.version_string(),
              default_config_files=default_config_files)


def init_application():
    # initialize the config system
    conffile = _get_config_file()
    _parse_args([], default_config_files=[conffile])
    db_api.configure(conf.CONF)

    # initialize the logging system
    setup_logging(conf.CONF)

    # dump conf at debug (log_options option comes from oslo.service)
    # FIXME(mriedem): This is gross but we don't have a public hook into
    # oslo.service to register these options, so we are doing it manually for
    # now; remove this when we have a hook method into oslo.service.
    conf.CONF.register_opts(service_opts.service_opts)
    if conf.CONF.log_options:
        conf.CONF.log_opt_values(
            logging.getLogger(__name__),
            logging.DEBUG)

    # build and return our WSGI app
    return deploy.loadapp(conf.CONF)
