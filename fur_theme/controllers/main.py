# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request

from odoo.addons.http_routing.models.ir_http import slug, unslug


class FurProjectController(http.Controller):
    _projects_per_page = 9

    def _project_domain(self, project_type=None):
        domain = request.website.website_domain() + [("is_published", "=", True)]
        if project_type:
            domain = domain + [("project_type", "=", project_type)]
        return domain

    def sitemap_projects(env, rule, qs):
        if not qs or qs.lower() in "/projects":
            yield {"loc": "/projects"}
        website = env["website"].get_current_website()
        projects = env["fur.project"].search(website.website_domain() + [("is_published", "=", True)])
        for project in projects:
            loc = "/projects/%s" % slug(project)
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    @http.route(
        ["/projects", "/projects/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_projects,
    )
    def projects(self, page=1, project_type=None, **kwargs):
        Project = request.env["fur.project"]
        types = dict(Project._fields["project_type"]._description_selection(request.env))
        if project_type not in types:
            project_type = None
        domain = self._project_domain(project_type)
        total = Project.search_count(domain)
        pager = request.website.pager(
            url="/projects",
            url_args={"project_type": project_type} if project_type else None,
            total=total,
            page=page,
            step=self._projects_per_page,
        )
        projects = Project.search(domain, limit=self._projects_per_page, offset=pager["offset"])
        return request.render(
            "fur_theme.projects_page",
            {
                "projects": projects,
                "pager": pager,
                "project_types": types,
                "current_type": project_type,
            },
        )

    @http.route(
        ["/projects/<string:project_slug>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,  # covered by sitemap_projects
    )
    def project_detail(self, project_slug, **kwargs):
        # not a model("fur.project") converter: an unpublished project is a
        # 404, not an access error
        website = request.website
        project = request.env["fur.project"].sudo().with_context(active_test=False).browse(
            unslug(project_slug)[1] or 0
        ).exists()
        if not project or (project.website_id and project.website_id != website):
            raise request.not_found()
        is_designer = request.env.user.has_group("website.group_website_designer")
        if not (project.active and project.website_published) and not is_designer:
            raise request.not_found()
        project = project.with_user(request.env.user).with_context(request.env.context)
        others = request.env["fur.project"].search(
            self._project_domain() + [("id", "!=", project.id)], limit=3
        )
        return request.render(
            "fur_theme.project_detail_page",
            {"project": project, "main_object": project, "other_projects": others},
        )
