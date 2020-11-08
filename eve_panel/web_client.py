import panel as pn
import param

CSS = """
body {
    overflow-y: hidden;
}

.pnx-nav-buttons {
    display: block;
    text-align: left;
    text-transform: uppercase;
    width: 100%;

}
.pnx-nav-buttons details {
    outline:none;
    width: 100%;
}
.pnx-nav-buttons summary {
    outline:none;
    width: 100%;
}

.pnx-nav-buttons a, .pnx-nav-buttons summary {
    display: block;
    text-decoration: none;
    padding-top: 0.5em;
    padding-bottom: 0.5em;
    padding-right: 1em;
    padding-left: 1em;
}
.pnx-nav-buttons a:hover {
    border-radius: 2px;
}
.pnx-nav-buttons a:active {
    border-radius: 2px;
}
"""

LINK_HTML = """
<a href="{link}">{name}</a>
"""

GROUP_HTML = """
<details><summary>{title}</summary>
{links_str}
{sub_groups_str}
</details>
"""

MENU_HTML = """
<div class="pnx-nav-buttons">
{groups_str}
</div>

"""

def make_group(title, links):
    sub_links = []
    sub_groups = []
    for name, link in links.items():
        if isinstance(link, dict):
            sub_groups.append(make_group(name, link)) 
        else:
            sub_links.append(LINK_HTML.format(name=name, link=link))
    links_str = "\n".join(sub_links)
    sub_groups_str = "\n".join(sub_groups)
    return GROUP_HTML.format(title=title, links_str=links_str, sub_groups_str=sub_groups_str)

def make_menu_html(links):
    groups = [make_group(k, v) for k,v in links.items()]
    groups_str = "\n".join(groups)
    return MENU_HTML.format(groups_str=groups_str)

def recursive_get(tree, path, sep="."):
    if path in tree:
        return tree[path]
    key, _, subpath = path.partition(sep)
    if key in tree:
        return recursive_get(tree[key], subpath)
    return None

class EveWebClient(param.Parameterized):
    resources = param.Dict({})
    path_args = param.String("")
    location = param.Parameter()
    title = param.String("Eve Client")
    width = param.Integer(default=250)

    def __init__(self, **params):
        if "location" not in params:
            params["location"] = pn.state.location
        super().__init__(**params)

    def template(self, **kwargs):
        
        self.location = pn.state.location
        pn.config.raw_css.append(CSS)
        tmpl = pn.template.MaterialTemplate(**kwargs)
        tmpl.sidebar[:] = [self.menu_view()]
        tmpl.main[:] = [pn.panel("# No resource selected.")]
        self._template = tmpl
        return tmpl

    @param.depends("location.search", watch=True)
    def main_view(self):
        resource_path = pn.state.session_args.get("resource", [b""])[0].decode()
        resource = recursive_get(self.resources, resource_path)
        if resource is not None:
            self._template.main[:] = [resource.panel()]

    @param.depends("resources")
    def menu_view(self):
        return self.make_menu(self.resources, max_width=self.width)
    
    def make_paths(self, tree: dict, parent="",):
        paths = {}
        for k,v in tree.items():
            path = ".".join([parent, k]).strip(".")
            if isinstance(v, dict):
                paths[k] = self.make_paths(v, path)
            else:
                paths[k] = f"?resource={path}"
        return paths

    def make_menu(self, tree, max_width=250):
        paths = self.make_paths(tree)
        html = make_menu_html(paths)
        return pn.pane.HTML(html, max_width=max_width)