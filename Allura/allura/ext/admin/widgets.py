from pylons import g, c

import ew as ew_core
from ew import jinja2_ew as ew

from allura import model as M
from allura.lib import validators as V
from allura.lib.widgets import forms as ff

class CardField(ew_core.Widget):
    template = 'jinja:admin_widgets/card_field.html'
    defaults = dict(
        ew_core.Widget.defaults,
        id=None,
        name='Deck',
        icon_name='group',
        items=None,
        settings_href=None)

    def item_display(self, item):
        return repr(item)

    def item_id(self, item):
        return repr(item)

    def resources(self):
        yield ew.CSSScript('''.deck li input, .deck li select {
margin: 2px 0 2px 3px;
width: 148px;
}''')
        yield ew.JSScript('''$(function() {
    $('.active-card').each(function() {
        var newitem = $('.new-item', this);
        var adder = $('.adder', this);
        var deleters = $('.deleter', this);
        newitem.remove();
        newitem.removeClass('new-item');
        deleters.click(function(evt) {
            evt.stopPropagation();
            evt.preventDefault();
            var $this = $(this);
            $this.closest('li').remove();
        });
        adder.click(function(evt) {
            evt.stopPropagation();
            evt.preventDefault();
            newitem.clone().insertBefore(adder.closest('li'));
        });
    });
})''')

class GroupCard(CardField):
    new_item=ew.InputField(attrs=dict(placeholder='type a username'))

    def item_display(self, user):
        return user.username

    def item_id(self, user):
        return user._id

class _GroupSelect(ew.SingleSelectField):

    def options(self):
        roles = sorted(
            (role for role in c.project.roles if role.name),
            key=lambda r:r.name)
        options = [
            ew.Option(py_value=role._id, label=role.name)
            for role in roles ]
        return options

class PermissionCard(CardField):
    new_item = _GroupSelect()

    def item_display(self, role):
        return role.name

    def item_id(self, role):
        return role._id


class GroupSettings(ew.SimpleForm):
    submit_text=None

    class hidden_fields(ew_core.NameList):
        _id = ew.HiddenField(
            validator=V.Ming(M.ProjectRole))

    class fields(ew_core.NameList):
        name = ew.InputField(label='Name')

    class buttons(ew_core.NameList):
        save = ew.SubmitButton(label='Save')
        delete = ew.SubmitButton(label='Delete Group')

class NewGroupSettings(ff.AdminForm):
    submit_text='Save'
    class fields(ew_core.NameList):
        name = ew.InputField(label='Name')