import os
import sys
import json
import logging

from pylons import g

from ming.orm import state, session

from pymongo.json_util import default
from pyforge import model as M

log = logging.getLogger(__name__)

MONGO_HOME=os.environ.get('MONGO_HOME', '')
MONGO_DUMP=os.path.join(MONGO_HOME, 'bin/mongodump')
MONGO_RESTORE=os.path.join(MONGO_HOME, 'bin/mongorestore')

def main():
    if len(sys.argv) != 2:
        log.error('Usage: %s <shortname>', sys.argv[0])
        return
    pname = sys.argv[1]
    log.info('Purging %s', pname)
    project = M.Project.query.get(shortname=pname)
    if project is None:
        log.fatal('Project %s not found', pname)
        return
    purge_project(project)

def purge_project(project):
    gid = project.tool_data.get('sfx', {}).get('group_id', project._id)
    project.shortname = 'deleted-%s' % gid
    project.deleted = True
    g.solr.delete(q='project_id_s:%s' % project._id)
    session(project).flush()

if __name__ == '__main__':
    main()