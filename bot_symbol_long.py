
import numpy as np
from bot_database import sql_session
from sqlalchemy import exc

class Symbol_long(object):

    def __init__(self, params, master) -> None:
        
        self.master = master
        self.params = params
        self.drop = params['drop']
        self.profit = params['profit']
        self.k = params['k']
        self.buy_trail = params['buy_trail']
        self.sell_trail = params['sell_trail']
        self.drop_param = params['drop_param']
        self.level = params['level']
        self.pond = params['pond']        
        self.asset = params['asset']
        self.tic = self.asset + self.master.account.base_coin
        self.name = self.asset + '--L'
        self.side = 'Long'
        self.nick = str(abs(self.drop)) + str(self.profit) + str(self.k)

        self.switch = True
        self.status = False
        self.can_open = False
        self.can_average = False
        self.can_close = False
        self.can_open_trail = False
        self.can_average_trail = False
        self.can_close_trail = False
    
        self.open_price = []
        self.open_time = []
        self.close_time = []
        self.duration = '0'
        self.acc = 0
        self.open_amount_list = np.array([])
        self.open_price_list = np.array([])
        self.open_asset_amount_list = np.array([])
        self.asset_acc = 0     
        self.asset_average_price = 0
        self.buy_amount = 0
        self.average_point = 0.0000000001
        self.close_point = 1000000000
        # self.average_price = 0
        self.buy_level = 0
        self.price = []
        self.live_profit = 0
        
        self.base_open_trail = 0
        self.base_average_trail = 0
        self.base_close_trail = 0
        
        self.interp_range = np.array(np.arange(0,50),dtype='float64')
        self.buy_distribution = np.cumsum(self.k**np.array(np.arange(0,50)) * self.master.account.initial_amount).astype('float64')
        self.drop_limit = 10
        self.drop_distribution = (1**np.array(np.arange(0,50)) * self.drop).astype('float64')
        self.drop_distribution[self.drop_limit:] = self.drop_distribution[self.drop_limit:] + self.drop_param

        self.timer = 0
        self.commission = 0
        self.order_id = 0

        self.open_order_id = []
        
        self.last_buy_price = []
        
    def trading_points(self):
        
        drop = np.interp(self.buy_level, self.interp_range, self.drop_distribution)        
        self.average_point = self.last_buy_price * (1 - drop/100)
        self.close_point = self.asset_average_price * (1 + self.profit/100)
        return
        
    def open_trailing(self, time, price):
        
        if price < self.base_open_trail:
            self.base_open_trail = price
            self.open_trail_point = self.base_open_trail*(1 + self.buy_trail/100)

            open_order = self.master.account.client.get_margin_order(symbol=self.open_order_id['symbol'], orderId=self.open_order_id['orderId'], isIsolated='TRUE')

            if open_order['status'] == 'FILLED':
                self.master.account.check_filled_order(self)

            elif open_order['status'] == 'NEW':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                buy_amount = np.interp(0, self.interp_range, self.buy_distribution)
                check = self.master.account.create_buy_order(self, buy_amount/self.open_trail_point, self.open_trail_point, 'OPEN')

            elif open_order['status'] == 'PARTIALLY FILLED':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                partial_amount, partial_price = self.master.account.check_partial_order(self)
                self.master.account.funds = self.master.account.funds - partial_amount*partial_price
                self.master.account.long_acc = self.master.account.long_acc + partial_amount*partial_price
                buy_amount = np.interp(0, self.interp_range, self.buy_distribution)
                check = self.master.account.create_buy_order(self, (buy_amount/self.open_trail_point - partial_amount), self.open_trail_point, 'OPEN')

        return
        
    def open_order(self, time, price, amount, comision):
        
        self.open_time = time
        self.open_price = price

        self.open_amount_list = np.append(self.open_amount_list, [amount*price])
        self.acc = np.sum([self.open_amount_list])
        self.open_asset_amount_list = np.append(self.open_asset_amount_list, [amount])
        self.asset_acc = np.sum([self.open_asset_amount_list])
        self.open_price_list = np.append(self.open_price_list, [price])
        self.asset_average_price = np.dot(self.open_price_list, self.open_asset_amount_list)/self.asset_acc
        self.master.account.funds = self.master.account.funds - amount*price
        self.master.account.long_acc = self.master.account.long_acc + amount*price
        
        drop = np.interp(self.buy_level, self.interp_range, self.drop_distribution)

        self.average_point = price * (1 - drop/100)
        self.close_point = self.asset_average_price * (1 + self.profit/100)
    
        self.status = True
        self.can_average = True
        self.can_close = True
        self.can_open_trail = False
        
        self.master.wr_list[self.nick][self.side] = self.acc/self.master.account.max_leverage_funds*100
        new_row = self.master.account.notifier.tables['ponderation'](Date=str(time), Name=self.name, Long_ratio=self.master.wr_list[self.nick]['Long'], Short_ratio=self.master.wr_list[self.nick]['Short'])
        sql_session.add(new_row)
        sql_session.commit()
        
        self.master.account.notifier.send_open_order_filled(price, amount, self)
        
        new_row = self.master.account.notifier.tables['funds'](Date=str(time), Funds=self.master.account.funds, Long_funds=self.master.account.long_acc, Short_funds=self.master.account.short_acc)
        sql_session.add(new_row)
        new_row = self.master.account.notifier.tables['orders'](Date=str(time), Name=self.name, Asset=self.asset, Side=self.side, Type='Buy', BuyLevel=self.buy_level, Price=price, Amount=amount, Cost=round(self.acc), Commission=comision, Order_id=self.order_id)
        sql_session.add(new_row)
        try:
            sql_session.commit()
        except exc.OperationalError as e:
            print(f"Error de conexión a la base de datos: {e}")
            self.master.account.notifier.send_error(self.name, f"Error de conexión a la base de datos: {e}")
            sql_session.rollback()
        
        self.last_buy_price = price

        return
    
    def average_trailing(self, time, price):

        if price < self.base_average_trail:
            self.base_average_trail = price
            self.average_trail_point = self.base_average_trail*(1 + self.buy_trail/100)
            
            open_order = self.master.account.client.get_margin_order(symbol=self.open_order_id['symbol'], orderId=self.open_order_id['orderId'], isIsolated='TRUE')
            
            if open_order['status'] == 'FILLED':
                self.master.account.check_filled_order(self)

            elif open_order['status'] == 'NEW':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                buy_amount = self.calculate_interp()
                check = self.master.account.create_buy_order(self, buy_amount/self.average_trail_point, self.average_trail_point, 'AVERAGE')
            
            elif open_order['status'] == 'PARTIALLY FILLED':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                partial_amount, partial_price = self.master.account.check_partial_order(self)
                self.master.account.funds = self.master.account.funds - partial_amount*partial_price
                self.master.account.long_acc = self.master.account.long_acc + partial_amount*partial_price
                buy_amount = self.calculate_interp()           
                check = self.master.account.create_buy_order(self, (buy_amount/self.average_trail_point - partial_amount), self.average_trail_point, 'AVERAGE')


        return

    def average_order(self, time, price, amount, comision):
        
        self.open_amount_list = np.append(self.open_amount_list, [amount*price])
        self.acc = np.sum([self.open_amount_list])
        self.open_asset_amount_list = np.append(self.open_asset_amount_list, [amount])
        self.asset_acc = np.sum([self.open_asset_amount_list])
        self.open_price_list = np.append(self.open_price_list, [price])
        self.asset_average_price = np.dot(self.open_price_list, self.open_asset_amount_list)/self.asset_acc
        self.master.account.funds = self.master.account.funds - amount*price
        self.master.account.long_acc = self.master.account.long_acc + amount*price
        
        total_drop = (1 - price/self.open_price) * 100
        if total_drop <= self.drop_limit*self.drop:
            self.buy_level = round(total_drop / self.drop, 1)
        else:
            self.buy_level = round(((total_drop - self.drop_limit*self.drop) / (self.drop + self.drop_param) + self.drop_limit), 1)
            
        last_drop = (1 - price/self.last_buy_price) * 100
    
        drop = np.interp(self.buy_level, self.interp_range, self.drop_distribution)
        self.average_point = price * (1 - drop/100)
        self.close_point = self.asset_average_price * (1 + self.profit/100) 

        self.can_average = True
        self.can_average_trail = False
        
        self.master.account.notifier.send_average_order_filled(price, amount, self, last_drop)
        
        new_row = self.master.account.notifier.tables['funds'](Date=str(time), Funds=self.master.account.funds, Long_funds=self.master.account.long_acc, Short_funds=self.master.account.short_acc)
        sql_session.add(new_row)
        new_row = self.master.account.notifier.tables['orders'](Date=str(time), Name=self.name, Asset=self.asset, Side=self.side, Type='Buy', BuyLevel=self.buy_level, Price=price, Amount=amount, Cost=round(self.acc), Commission=comision, Order_id=self.order_id)
        sql_session.add(new_row)
        try:
            sql_session.commit()
        except exc.OperationalError as e:
            print(f"Error de conexión a la base de datos: {e}")
            self.master.account.notifier.send_error(self.name, f"Error de conexión a la base de datos: {e}")
            sql_session.rollback()
            
        self.last_buy_price = price
        
        self.master.wr_list[self.nick][self.side] = self.acc/self.master.account.max_leverage_funds*100
        new_row = self.master.account.notifier.tables['ponderation'](Date=str(time), Name=self.name, Long_ratio=self.master.wr_list[self.nick]['Long'], Short_ratio=self.master.wr_list[self.nick]['Short'])
        sql_session.add(new_row)
        sql_session.commit()
        
        return
    
    def close_trailing(self, time, price):

        if price < self.base_close_trail:
            self.base_close_trail = price
            self.close_trail_point = self.base_close_trail*(1 - self.sell_trail/100)

            open_order = self.master.account.client.get_margin_order(symbol=self.open_order_id['symbol'], orderId=self.open_order_id['orderId'], isIsolated='TRUE')

            if open_order['status'] == 'FILLED':
                self.master.account.check_filled_order(self)

            elif open_order['status'] == 'NEW':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                check = self.master.account.create_sell_order(self, self.asset_acc, self.close_trail_point, 'CLOSE')

            elif open_order['status'] == 'PARTIALLY FILLED':
                self.master.account.client.cancel_margin_order(symbol=self.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                self.open_order_id = []
                partial_amount, partial_price = self.master.account.check_partial_order(self)
                self.master.account.funds = self.master.account.funds + partial_amount*partial_price
                self.master.account.long_acc = self.master.account.long_acc - partial_amount*partial_price
                check = self.master.account.create_sell_order(self, self.asset_acc, self.close_trail_point, 'CLOSE')

        return

    def close_order(self, time, price, amount, comision):
                
        profit = (price/self.asset_average_price - 1)
        usd_profit = profit * self.acc - self.commission
        self.duration = time - self.open_time
        self.master.account.funds = self.master.account.funds + amount*price
        self.master.account.long_acc = self.master.account.long_acc - self.acc
        
        covered = round(((1 - self.last_buy_price/self.open_price) * 100), 2)

        self.master.account.notifier.send_transaction_closed_filled(self, profit, usd_profit, self.commission, price, covered)
        
        new_row = self.master.account.notifier.tables['funds'](Date=str(time), Funds=self.master.account.funds, Long_funds=self.master.account.long_acc, Short_funds=self.master.account.short_acc)
        sql_session.add(new_row)
        new_row = self.master.account.notifier.tables['orders'](Date=str(time), Name=self.name, Asset=self.asset, Side=self.side, Type='Sell', BuyLevel=self.buy_level, Price=price, Amount=amount, Cost=round(self.acc), Commission=comision, Order_id=self.order_id)
        sql_session.add(new_row)
        new_row = self.master.account.notifier.tables['transactions'](Date=str(time), Name=self.name, Asset=self.asset, Side=self.side, BuyLevel=self.buy_level, Cost=round(self.acc), Profit=profit*100, ProfitUsd=float(usd_profit), Commission=self.commission, Duration=str(self.duration))
        sql_session.add(new_row)
        try:
            sql_session.commit()
        except exc.OperationalError as e:
            print(f"Error de conexión a la base de datos: {e}")
            self.master.account.notifier.send_error(self.name, f"Error de conexión a la base de datos: {e}")
            sql_session.rollback()
        
        # print('#TRANSACTION_CLOSED ' + str(self.name) + '\n' + 'Close Price: ' + str(price) + '\n' + 'Duration: ' + str(self.duration) + '\n' + 'Buy Level: ' + str(self.buy_level) + '\n' + 'Cost: ' + str(round(self.acc,2)) + '$ \n' + 'Profit: ' + str(round(profit*100, 2)) + '% \n' + 'Profit USD: ' + str(round(usd_profit,4)) + ' $\n' + 'Commision: ' + str(round(float(self.commission), 5)) + '\n' + 'USDT balance: ' + str(round(self.master.account.balances[self.master.account.base_coin], 2)))
        
        self.buy_amount = 0
        self.open_amount_list = np.array([])
        self.open_price_list = []
        self.open_asset_amount_list = np.array([])
        self.asset_acc = 0
        self.buy_level = 0
        self.acc = 0
        self.duration = '0'
        self.close_point = 1000000000
        self.live_profit = 0
        self.commission = 0
        self.order_id = self.order_id + 1
        
        self.master.wr_list[self.nick][self.side] = self.acc/self.master.account.max_leverage_funds*100
        new_row = self.master.account.notifier.tables['ponderation'](Date=str(time), Name=self.name, Long_ratio=self.master.wr_list[self.nick]['Long'], Short_ratio=self.master.wr_list[self.nick]['Short'])
        sql_session.add(new_row)
        sql_session.commit()
        
        self.status = False
        self.can_open = True
        self.can_average = False
        self.can_close = False
        self.can_close_trail = False
        
        return

    def logic(self, time, price):

        if self.status:
            self.live_profit = (price/self.asset_average_price - 1)
            self.duration = time - self.open_time

        open_order = self.master.account.client.get_margin_order(symbol=self.open_order_id['symbol'], orderId=self.open_order_id['orderId'], isIsolated='TRUE')
        if open_order['status'] == 'FILLED':
            self.master.account.check_filled_order(self)

        if self.can_open_trail:
            self.open_trailing(time, price)
            
        if self.can_open and self.switch:

            if self.master.wr_list[self.nick]['Short'] >= self.level:
                self.buy_distribution = np.cumsum(self.k**np.array(np.arange(0,50)) * self.master.account.initial_amount).astype('float64') * self.pond
                self.master.account.notifier.register_output('Info', self.name, self.side, 'Operation ponderated: ' + str(self.pond))
            elif self.master.wr_list[self.nick]['Short'] < self.level:
                self.buy_distribution = np.cumsum(self.k**np.array(np.arange(0,50)) * self.master.account.initial_amount).astype('float64')
                self.master.account.notifier.register_output('Info', self.name, self.side, 'Operation no ponderated')

            self.base_open_trail = price
            self.open_trail_point = self.base_open_trail*(1 + self.buy_trail/100)
            buy_amount = np.interp(0, self.interp_range, self.buy_distribution)
            check = self.master.account.create_buy_order(self, buy_amount/self.open_trail_point, self.open_trail_point, 'OPEN')
            if check:
                self.can_open_trail = True
                self.can_open = False

        if self.can_average_trail:
            self.average_trailing(time, price)
            
        if price < self.average_point and self.can_average:

            self.base_average_trail = price
            self.average_trail_point = self.base_average_trail*(1 + self.buy_trail/100)
            buy_amount = self.calculate_interp()              
            check = self.master.account.create_buy_order(self, buy_amount/self.average_trail_point, self.average_trail_point, 'AVERAGE')
            if check:
                self.can_average_trail = True
                self.can_average = False
                self.can_close_trail = False
                self.can_close = True

        if self.can_close_trail:
            self.close_trailing(time, price)
            
        if price > self.close_point and self.can_close:
            
            self.base_close_trail = price
            self.close_trail_point = self.base_close_trail*(1 - self.sell_trail/100)
            check = self.master.account.create_sell_order(self, self.asset_acc, self.close_trail_point, 'CLOSE')
            if check:
                self.can_average_trail = False
                self.can_average = True
                self.can_close_trail = True
                self.can_close = False
            
        return
    
    def calculate_interp(self):
        
        total_drop = (1 - self.average_trail_point/self.open_price) * 100
        if total_drop <= self.drop_limit*self.drop:
            buy_level = round(total_drop / self.drop, 1)
        else:
            buy_level = round(((total_drop - self.drop_limit*self.drop) / (self.drop + self.drop_param) + self.drop_limit), 1)
        buy_amount = np.interp(buy_level, self.interp_range, self.buy_distribution) - self.acc      

        return buy_amount   
    
__all__ = ['Symbol_long']
