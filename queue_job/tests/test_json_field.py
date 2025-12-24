# copyright 2016 Camptocamp
# license lgpl-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import json
from datetime import date, datetime

from lxml import etree

from .common import TransactionCase

# pylint: disable=odoo-addons-relative-import
# we are testing, we want to test as we were an external consumer of the API
from odoo.addons.queue_job.fields import JobDecoder, JobEncoder


class TestJson(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Queue Job JSON Partner"})
        user_partner = cls.env["res.partner"].create({"name": "Queue Job JSON User"})
        cls.demo_user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Queue Job JSON User",
                    "login": "queue_job_json_user",
                    "email": "queue.job.json@example.com",
                    "partner_id": user_partner.id,
                    "company_id": cls.env.company.id,
                    "company_ids": [(6, 0, cls.env.companies.ids)],
                    "tz": cls.env.user.tz or "UTC",
                    "lang": cls.env.user.lang or "en_US",
                }
            )
        )

    def _partner_with_user_context(self, context):
        return (
            self.env(user=self.demo_user, context=context)["res.partner"]
            .browse(self.partner.id)
        )

    def test_encoder_recordset(self):
        context = self.demo_user.context_get()
        partner = self._partner_with_user_context(context)
        value = partner
        value_json = json.dumps(value, cls=JobEncoder)
        expected_context = context.copy()
        expected_context.pop("uid")
        expected = {
            "uid": self.demo_user.id,
            "_type": "odoo_recordset",
            "model": "res.partner",
            "ids": [partner.id],
            "su": False,
            "context": expected_context,
        }
        self.assertEqual(json.loads(value_json), expected)

    def test_encoder_recordset_list(self):
        context = self.demo_user.context_get()
        partner = self._partner_with_user_context(context)
        value = ["a", 1, partner]
        value_json = json.dumps(value, cls=JobEncoder)
        expected_context = context.copy()
        expected_context.pop("uid")
        expected = [
            "a",
            1,
            {
                "uid": self.demo_user.id,
                "_type": "odoo_recordset",
                "model": "res.partner",
                "ids": [partner.id],
                "su": False,
                "context": expected_context,
            },
        ]
        self.assertEqual(json.loads(value_json), expected)

    def test_decoder_recordset(self):
        context = self.demo_user.context_get()
        partner = self._partner_with_user_context(context)

        value_json = json.dumps(
            {
                "_type": "odoo_recordset",
                "model": "res.partner",
                "su": False,
                "ids": partner.ids,
                "uid": self.demo_user.id,
                "context": {"tz": context["tz"], "lang": context["lang"]},
            }
        )

        expected = partner
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)
        self.assertEqual(self.demo_user, expected.env.user)

    def test_decoder_recordset_list(self):
        context = self.demo_user.context_get()
        partner = self._partner_with_user_context(context)
        value_json = json.dumps(
            [
                "a",
                1,
                {
                    "_type": "odoo_recordset",
                    "model": "res.partner",
                    "su": False,
                    "ids": partner.ids,
                    "uid": self.demo_user.id,
                    "context": {"tz": context["tz"], "lang": context["lang"]},
                },
            ]
        )
        expected = ["a", 1, partner]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)
        self.assertEqual(self.demo_user, expected[2].env.user)

    def test_decoder_recordset_list_without_user(self):
        value_json = (
            '["a", 1, {"_type": "odoo_recordset",' '"model": "res.users", "ids": [1]}]'
        )
        expected = ["a", 1, self.env.ref("base.user_root")]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)

    def test_encoder_datetime(self):
        value = ["a", 1, datetime(2017, 4, 19, 8, 48, 50, 1)]
        value_json = json.dumps(value, cls=JobEncoder)
        expected = [
            "a",
            1,
            {"_type": "datetime_isoformat", "value": "2017-04-19T08:48:50.000001"},
        ]
        self.assertEqual(json.loads(value_json), expected)

    def test_decoder_datetime(self):
        value_json = (
            '["a", 1, {"_type": "datetime_isoformat",'
            '"value": "2017-04-19T08:48:50.000001"}]'
        )
        expected = ["a", 1, datetime(2017, 4, 19, 8, 48, 50, 1)]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)

    def test_encoder_date(self):
        value = ["a", 1, date(2017, 4, 19)]
        value_json = json.dumps(value, cls=JobEncoder)
        expected = ["a", 1, {"_type": "date_isoformat", "value": "2017-04-19"}]
        self.assertEqual(json.loads(value_json), expected)

    def test_decoder_date(self):
        value_json = '["a", 1, {"_type": "date_isoformat",' '"value": "2017-04-19"}]'
        expected = ["a", 1, date(2017, 4, 19)]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        self.assertEqual(value, expected)

    def test_encoder_etree(self):
        etree_el = etree.Element("root", attr="val")
        etree_el.append(etree.Element("child", attr="val"))
        value = ["a", 1, etree_el]
        value_json = json.dumps(value, cls=JobEncoder)
        expected = [
            "a",
            1,
            {
                "_type": "etree_element",
                "value": '<root attr="val"><child attr="val"/></root>',
            },
        ]
        self.assertEqual(json.loads(value_json), expected)

    def test_decoder_etree(self):
        value_json = '["a", 1, {"_type": "etree_element", "value": \
        "<root attr=\\"val\\"><child attr=\\"val\\"/></root>"}]'
        etree_el = etree.Element("root", attr="val")
        etree_el.append(etree.Element("child", attr="val"))
        expected = ["a", 1, etree.tostring(etree_el)]
        value = json.loads(value_json, cls=JobDecoder, env=self.env)
        value[2] = etree.tostring(value[2])
        self.assertEqual(value, expected)
