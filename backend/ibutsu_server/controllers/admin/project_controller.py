import connexion
from flask import abort
from ibutsu_server.db.base import session
from ibutsu_server.db.models import Project
from ibutsu_server.db.models import User
from ibutsu_server.util.admin import check_user_is_admin
from ibutsu_server.util.uuid import convert_objectid_to_uuid
from ibutsu_server.util.uuid import is_uuid


def add_project(project=None, token_info=None, user=None):
    """Create a project

    :param body: Project
    :type body: dict | bytes

    :rtype: Project
    """
    check_user_is_admin(user)
    if not connexion.request.is_json:
        return "Bad request, JSON required", 400
    project = Project.from_dict(**connexion.request.get_json())
    user = User.query.get(user)
    if user:
        project.owner = user
        project.users.append(user)
    session.add(project)
    session.commit()
    return project.to_dict(), 201


def get_project(id_, token_info=None, user=None):
    """Get a single project by ID

    :param id: ID of test project
    :type id: str

    :rtype: Project
    """
    check_user_is_admin(user)
    project = Project.query.get(id_)
    if not project:
        project = Project.query.filter(Project.name == id_).first()
    if not project:
        abort(404)
    return project.to_dict()


def get_project_list(
    owner_id=None, group_id=None, page=1, page_size=25, token_info=None, user=None
):
    """Get a list of projects

    :param owner_id: Filter projects by owner ID
    :type owner_id: str
    :param group_id: Filter projects by group ID
    :type group_id: str
    :param limit: Limit the projects
    :type limit: int
    :param offset: Offset the projects
    :type offset: int

    :rtype: List[Project]
    """
    check_user_is_admin(user)
    query = Project.query
    if owner_id:
        query = query.filter(Project.owner_id == owner_id)
    if group_id:
        query = query.filter(Project.group_id == group_id)
    offset = (page * page_size) - page_size
    total_items = query.count()
    total_pages = (total_items // page_size) + (1 if total_items % page_size > 0 else 0)
    projects = query.offset(offset).limit(page_size).all()
    return {
        "projects": [project.to_dict() for project in projects],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total_items,
            "totalPages": total_pages,
        },
    }


def update_project(id_, project=None, token_info=None, user=None):
    """Update a project

    :param id: ID of test project
    :type id: str
    :param body: Project
    :type body: dict | bytes

    :rtype: Project
    """
    check_user_is_admin(user)
    if not connexion.request.is_json:
        return "Bad request, JSON required", 400
    if not is_uuid(id_):
        id_ = convert_objectid_to_uuid(id_)
    project = Project.query.get(id_)

    if not project:
        abort(404)

    # handle updating users separately
    updates = connexion.request.get_json()
    for username in updates.pop("users", []):
        user_to_add = User.query.filter_by(email=username).first()
        if user_to_add and user_to_add not in project.users:
            project.users.append(user_to_add)

    # update the rest of the project info
    project.update(updates)
    session.add(project)
    session.commit()
    return project.to_dict()


def delete_project(id_, token_info=None, user=None):
    """Delete a single project"""
    check_user_is_admin(user)
    project = Project.query.get(id_)
    if not project:
        abort(404)
    session.delete(project)
    session.commit()
    return "OK", 200