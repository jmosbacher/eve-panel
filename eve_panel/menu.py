import panel as pn
import param

css = '''
.bk.panel-menu-button {
  background: #f0f0f0;
  border-radius: 0px;
  border: 1px black solid;
}
'''

class Menu(param.Parameterized):
    resources = param.Dict({})
    selected = param.String()
    resource_by_name = param.Dict({})
    width = param.Integer(default=250)
         
    @param.depends("selected")
    def selected_view(self):
        if self.selected and self.selected in self.resource_by_name:
            item = self.resource_by_name[self.selected]
            return item.panel()
        else:
            return pn.Column("# No resource selected.")
        
    @param.depends("resources")
    def menu_view(self):
        menu = self.generate_menu(self.resources, width=self.width)
        view = pn.Column(
            pn.pane.Markdown("## Resources", margin=2),
            pn.layout.Divider(margin=2,),
            menu,
            pn.layout.Divider(margin=2,),
            width_policy='max',
            sizing_mode='stretch_width',
            max_width=self.width,
        )
        return view
    
    def make_callback(self, name):
        def cb(event):
            self.selected = name
        cb.__name__ = f"{name}_callback"
        return cb
    
    def generate_menu(self, tree, width=250):
        groups = pn.layout.Accordion(width=width, toggle=True, margin=(5, 5, 5, 5))
        buttons = []
        for k,v in tree.items():
            if isinstance(v, dict):
                groups.append((k.replace("_", " ").title(), self.generate_menu(v, width=width-10)))
            else:
                self.resource_by_name[v.name] = v
                button = pn.widgets.Button(name=f"{k.replace('_', ' ').title()}",
                    max_height=70,
                    sizing_mode="stretch_width",
                    max_width=width,
                    css_classes=['panel-menu-button'],
                    margin=(0,0,0,0), 
                    )
                button.on_click(self.make_callback(v.name))
                buttons.append(button)
            
        if len(groups):
            items = [groups] + buttons
        else:
            items = buttons
        return pn.Column(
                *items, 
                width_policy='max',
                sizing_mode='stretch_width',
                max_width=width)