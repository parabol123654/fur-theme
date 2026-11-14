# Part of Fur Theme. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.fields import Domain
from odoo.http import request


class FurProjectController(http.Controller):
    _projects_per_page = 9

    def _project_domain(self, project_type=None):
        domain = request.env.website.website_domain() & Domain("is_published", "=", True)
        if project_type:
            domain &= Domain("project_type", "=", project_type)
        return domain

    def sitemap_projects(env, rule, qs):
        if not qs or qs.lower() in "/projects":
            yield {"loc": "/projects"}
        slug = env["ir.http"]._slug
        projects = env["fur.project"].search(
            env.website.website_domain() & Domain("is_published", "=", True)
        )
        for project in projects:
            loc = f"/projects/{slug(project)}"
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
        pager = request.env.website.pager(
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
        ['/projects/<model("fur.project"):project>'],
        type="http",
        auth="public",
        website=True,
        sitemap=False,  # covered by sitemap_projects
    )
    def project_detail(self, project, **kwargs):
        website = request.env.website
        if project.website_id and project.website_id != website:
            raise request.not_found()
        is_designer = request.env.user.has_group("website.group_website_designer")
        if not (project.active and project.website_published) and not is_designer:
            raise request.not_found()
        others = request.env["fur.project"].search(
            self._project_domain() & Domain("id", "!=", project.id), limit=3
        )
        return request.render(
            "fur_theme.project_detail_page",
            {"project": project, "main_object": project, "other_projects": others},
        )
