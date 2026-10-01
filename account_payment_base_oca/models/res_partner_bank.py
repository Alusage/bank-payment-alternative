# Copyright 2023-2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

SCRAMBLE_CHAR = "*"
BIC_REGEX = re.compile(r"[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3})?$")


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    acc_number_scrambled = fields.Char(compute="_compute_acc_number_scrambled")

    def _do_scramble(
        self, letter, position_from_start, position_from_end, first_n, last_n
    ):
        if (
            first_n
            and position_from_start <= first_n
            or last_n
            and position_from_end <= last_n
        ):
            return False
        return True

    def _scramble_acc_number(self, account_number, first_n, last_n):
        # scramble account number and while keeping spaces
        scrambled_number_list = list(account_number)
        position_from_start = 1
        position_from_end = len(account_number.replace(" ", ""))
        position = 0
        for letter in account_number:
            if letter != " ":
                do_scramble = self._do_scramble(
                    letter, position_from_start, position_from_end, first_n, last_n
                )
                if do_scramble:
                    scrambled_number_list[position] = SCRAMBLE_CHAR
                position_from_start += 1
                position_from_end -= 1
            position += 1
        scrambled_acc_number = "".join(scrambled_number_list)
        return scrambled_acc_number

    def get_acc_number(self, show_policy, show_chars=4):
        self.ensure_one()
        assert show_policy in ("full", "first", "last", "first_last", "no")
        if not self.account_number or show_policy == "no":
            return ""
        if show_policy == "full":
            res = self.account_number
        elif show_policy == "first":
            res = self._scramble_acc_number(self.account_number, show_chars, 0)
        elif show_policy == "last":
            res = self._scramble_acc_number(self.account_number, 0, show_chars)
        elif show_policy == "first_last":
            res = self._scramble_acc_number(self.account_number, show_chars, show_chars)
        return res

    @api.depends("account_number")
    @api.depends_context("show_bank_account", "show_bank_account_chars")
    def _compute_acc_number_scrambled(self):
        policy = self.env.context.get("show_bank_account", "first_last")
        show_chars = self.env.context.get("show_bank_account_chars", 4)
        for rec in self:
            rec.acc_number_scrambled = rec.get_acc_number(policy, show_chars=show_chars)

    # Odoo 20 dropped the res.bank model; the BIC now lives on res.partner.bank
    # as the bank_bic char field, so the check moves here.
    @api.constrains("bank_bic")
    def _check_bic_length(self):
        for acc in self:
            if acc.bank_bic:
                if len(acc.bank_bic) not in (8, 11):
                    raise ValidationError(
                        self.env._(
                            "A valid BIC contains 8 or 11 characters. BIC '%(bic)s' "
                            "contains %(num)d characters, so it is not valid.",
                            bic=acc.bank_bic,
                            num=len(acc.bank_bic),
                        )
                    )
                if not BIC_REGEX.match(acc.bank_bic):
                    raise ValidationError(
                        self.env._(
                            "BIC '%(bic)s' doesn't respect the standard "
                            "pattern '{pattern}'.",
                            bic=acc.bank_bic,
                            pattern=BIC_REGEX.pattern,
                        )
                    )
