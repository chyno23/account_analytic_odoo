# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, fields

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    analytic = fields.Many2one(
        comodel_name='account.analytic.account',
        string = 'Analitica',
        domain="[('plan_id', '=', 'Contratacion')]",
        help = 'agregar la cuenta analitica que deseas utilizar'
    )

    picking_id = fields.Many2one('stock.picking', string='Picking')

    @api.model
    def create(self, vals):
        # Crea el registro en 'StockPicking' y luego actualiza los registros relacionados en 'StockMove'
        picking = super(StockPicking, self).create(vals)
        self.action_mi_boton()  

        return picking

    def write(self, vals):
        # Actualiza los registros en 'StockMove' antes de escribir en 'StockPicking'
        res = super(StockPicking, self).write(vals)
        self.action_mi_boton()  

        return res
    

    def action_mi_boton(self, context=None):
       
        for move in self.move_ids:
            move._onchange_analytic()

class StockMove(models.Model):
    _name = "stock.move"
    _inherit = ["stock.move", "analytic.mixin"]
    
    analytic = fields.Many2one(
        string='analitica heredado',
        related='picking_id.analytic'
    )

    move_ids = fields.One2many('stock.move', 'picking_id', string='Moves')
    
    @api.depends('analytic')
    def _compute_analytic_distribution(self):
        for move in self:
            if move.analytic:
                move.analytic_distribution = {move.analytic.id : 100}
            else:
                move.analytic_distribution = {}

    @api.onchange('analytic')
    def _onchange_analytic(self):
        if self.analytic:
            self.analytic_distribution = {self.analytic.id : 100}
        else:
            self.analytic_distribution = {}

    def _prepare_account_move_line(
        self, qty, cost, credit_account_id, debit_account_id, svl_id, description
    ):
        self.ensure_one()
        res = super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )
        if not self.analytic_distribution:
            return res
        for line in res:
            if (
                line[2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                # Add analytic account in debit line
                line[2].update({"analytic_distribution": self.analytic_distribution})
        return res

    def _prepare_procurement_values(self):
        """
        Allows to transmit analytic account from moves to new
        moves through procurement.
        """
        res = super()._prepare_procurement_values()
        if self.analytic_distribution:
            res.update(
                {
                    "analytic_distribution": self.analytic_distribution,
                }
            )
        return res

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """
        We fill in the analytic account when creating the move line from
        the move
        """
        res = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res
    


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = ["stock.move.line", "analytic.mixin"]

    @api.model
    def _prepare_stock_move_vals(self):
        """
        In the case move lines are created manually, we should fill in the
        new move created here with the analytic account if filled in.
        """
        res = super()._prepare_stock_move_vals()
        if self.analytic_distribution:
            res.update({"analytic_distribution": self.analytic_distribution})
        return res
