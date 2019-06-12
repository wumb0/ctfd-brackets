from CTFd.plugins.challenges import BaseChallenge, CHALLENGE_CLASSES
from CTFd.plugins import register_plugin_assets_directory, bypass_csrf_protection
from CTFd.models import db, ma, Challenges, Teams, Users
from CTFd.utils.decorators import admins_only
from CTFd.api import CTFd_API_v1
from flask_restplus import Namespace, Resource
from marshmallow_sqlalchemy import field_for
from flask import request


# models
tb = db.Table("team_bracket",
              db.Column("team_id", db.Integer, db.ForeignKey("teams.id")),
              db.Column("bracket_id", db.Integer, db.ForeignKey("brackets.id"))
              )

ub = db.Table("user_bracket",
              db.Column("user_id", db.Integer, db.ForeignKey("users.id")),
              db.Column("bracket_id", db.Integer, db.ForeignKey("brackets.id"))
              )

class Brackets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, index=True, unique=True)
    hidden = db.Column(db.Boolean)
    # super hacked up way to get the chal_bracket attribute on the parent
    # model class (Teams) without actually modifying it
    teams = db.relationship("Teams", backref=db.backref("chal_bracket", uselist=False),
                            secondary=tb, primaryjoin=id == tb.c.bracket_id,
                            secondaryjoin=Teams.id == tb.c.team_id)
    users = db.relationship("Users", backref=db.backref("chal_bracket", uselist=False),
                            secondary=ub, primaryjoin=id == ub.c.bracket_id,
                            secondaryjoin=Users.id == ub.c.user_id)

# schema
class BracketSchema(ma.ModelSchema):
    class Meta:
        model = Brackets
        include_fk = True
        dump_only = ('id',)


# API
brackets_namespace = Namespace('brackets', description='Endpoint to retrieve brackets')

@brackets_namespace.route('')
class BracketList(Resource):
    @admins_only
    def get(self):
        brackets = Brackets.query.all()
        schema = BracketSchema(many=True)
        result = schema.dump(brackets)
        if result.errors:
            return {
                'success': False,
                'errors': result.errors
            }, 400
        return {
            'success': True,
            'data': result.data
        }

    @admins_only
    def post(self):
        req = request.get_json()
        schema = BracketSchema()
        resp = schema.load(req, session=db.session)
        if resp.errors:
            return {
                'success': False,
                'errors': resp.errors
            }, 400
        db.session.add(resp.data)
        db.session.commit()

        resp = schema.dump(resp.data)
        db.session.close()

        return {
            'success': True,
            'data': resp.data
        }

def load(app):
    app.db.create_all()
    CTFd_API_v1.add_namespace(brackets_namespace, '/brackets')
