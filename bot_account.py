
import numpy as np
from datetime import datetime
import math
from binance.client import Client
from bot_database import sql_session
import traceback
from sqlalchemy import exc

class Margin_account():
    
    def __init__(self, notifier) -> None:
        
        self.notifier = notifier
        self.base_coin = 'USDT'
        self.assets = []
        self.available_funds = 0
        self.max_leverage = 10
        self.max_leverage_funds = self.available_funds * self.max_leverage
        self.initial_amount = 11
        
        self.nav = 0
        self.margin = 999
        self.funds = 0
        self.long_acc = 0
        self.short_acc = 0
        
        self.balances = {}
        self.loans = {}
        
        self.client = Client('HxC4DjBJjOv6lqiDdgnF1c7SW3SYYKnmvRyg1KAW4UY4oa5Ndbz3yAi7Z4TtXky9', 'RwwVEqxVzRmtcxf8sAvMcu6kwz6OxEtxsbcTBDTjgHrsmzqgpCjFcBq0aeW93rEU')
        self.price_precision = {'BTC':2, 'ETH':2, 'BNB':1, 'XRP':4, 'ADA':4, 'LTC':2, 'SOL':2, 'ATOM':3, 'BCH':1, 
                                'DOGE':5, 'DOT':3, 'EOS':3, 'LINK':3, 'TRX':5, 'USDT':2}
        self.amount_precision = {'BTC':5, 'ETH':4, 'BNB':3, 'XRP':0, 'ADA':1, 'LTC':3, 'SOL':2, 'ATOM':2, 'BCH':3, 
                                'DOGE':0, 'DOT':2, 'EOS':1, 'LINK':2, 'TRX':1, 'USDT':2}
        
        self.open_order_list = []
    
    def round_decimals_up(self, number, decimals):
        factor = 10 ** decimals
        return math.ceil(number * factor) / factor
    
    def round_decimals_down(self, number, decimals):
        factor = 10 ** decimals
        return math.floor(number * factor) / factor
    
    
    def get_initial_base_balances(self, asset):
        
        try:
            for item in self.client.get_isolated_margin_account()['assets']:
                if item['baseAsset']['asset'] == asset and item['quoteAsset']['asset'] == self.base_coin:
                    base_balance = float(self.round_decimals_down(float(item['quoteAsset']['free']), 2))
                    base_loan = float(self.round_decimals_down(float(item['quoteAsset']['borrowed']) + float(item['quoteAsset']['interest']), 2))
        except Exception as e:
            print(f"Get initial base balance error: {e}")
            traceback.print_exc()
            self.notifier.register_output('Error', asset, 'general', 'Get initial base balance error: ' + str(e))
        return base_balance, base_loan
    
    def get_base_balances(self, asset):
        
        if asset not in self.balances:
            self.balances[asset] = 0
        if asset not in self.loans:
            self.loans[asset] = 0

        try:
            for item in self.client.get_isolated_margin_account()['assets']:
                if item['baseAsset']['asset'] == asset and item['quoteAsset']['asset'] == self.base_coin:
                    self.balances[self.base_coin] = self.round_decimals_down(float(item['quoteAsset']['free']), 2)
                    self.loans[self.base_coin] = self.round_decimals_down(float(item['quoteAsset']['borrowed']) + float(item['quoteAsset']['interest']), 2)
        except Exception as e:
            print(f"Get base balance error: {e}")
            traceback.print_exc()
            self.notifier.register_output('Error', asset, 'general', 'Get base balance error: ' + str(e))
        return
    
    def get_asset_balances(self, asset, precision):
        
        try:
            for item in self.client.get_isolated_margin_account()['assets']:
                if item['baseAsset']['asset'] == asset and item['quoteAsset']['asset'] == self.base_coin:
                    self.balances[asset] = self.round_decimals_down(float(item['baseAsset']['free']), precision)
                    self.loans[asset] = self.round_decimals_down(float(item['baseAsset']['borrowed']) + float(item['baseAsset']['interest']), precision)
        except Exception as e:
            print(f"Get asset balance error: {e}")
            traceback.print_exc()
            self.notifier.register_output('Error', asset, 'general', 'Get asset balance error: ' + str(e))
        return
    
    def create_loan(self, order_qty, precision, asset, symbol):
        
        loan_qty = self.round_decimals_up(order_qty, precision)  
        try:
            max_loan = float(self.client.get_max_margin_loan(asset=asset, isolatedSymbol=symbol.tic)['amount'])
            order_ok = True
        except:
            max_loan = 0
            order_ok = False
            
        if max_loan > loan_qty and order_ok:
            print('Loan Creation Placed', asset, 'qty: ', loan_qty)
            try:
                self.client.create_margin_loan(asset=asset, amount=loan_qty, symbol=symbol.tic, isIsolated=True)
                order_ok = True
            except Exception as e:
                order_ok = False
                print(f"Loan creation failed: {e}")
                traceback.print_exc()
                self.notifier.register_output('Error', symbol.asset, symbol.side, 'Loan creation failed: ' + str(e))
            print('Loan Creation Filled', asset, 'qty: ', loan_qty)
            self.notifier.register_output('Action', symbol.asset, symbol.side, 'Loan Creation')
        else:
            print('Borrow limit', max_loan, loan_qty)
            order_ok = False
            self.notifier.register_output('Borrow Limit Excedeed', symbol.asset, symbol.side, 'Max Loan=' + str(max_loan) + ' Loan qty=' + str(loan_qty))
        return order_ok
    
    def repay_loan(self, symbol, amount, price, coin):

        
        self.get_asset_balances(symbol.asset, self.amount_precision[symbol.asset])
        self.get_base_balances(symbol.asset)
        print(self.loans)
        print(self.balances)
        
        if self.loans[symbol.asset] > 0 and self.balances[symbol.asset] > 0 and coin == 'Asset':
            repay = min(self.balances[symbol.asset], amount)
            loan_qty = self.round_decimals_down(repay, self.amount_precision[symbol.asset])
            print('Loan Repay Placed', symbol.asset, 'qty: ', loan_qty)
            self.client.repay_margin_loan(asset=symbol.asset, amount=loan_qty, symbol=symbol.tic, isIsolated=True)
            print('Loan Repay Filled', self.base_coin)     
            self.notifier.register_output('Action', symbol.asset, symbol.side, 'Loan Repaid')
                   
        if self.loans[self.base_coin] > 0 and self.balances[self.base_coin] > 0 and coin == 'Base':
            repay = min(self.balances[self.base_coin], amount*price)
            loan_qty = self.round_decimals_down(repay, 2)
            print('Loan Repay Placed', self.base_coin, 'qty: ', loan_qty)
            self.client.repay_margin_loan(asset=self.base_coin, amount=loan_qty, symbol=symbol.tic, isIsolated=True)
            print('Loan Repay Filled', self.base_coin)     
            self.notifier.register_output('Action', symbol.asset, symbol.side, 'Loan Repaid')
            
        self.extra_repay(symbol.asset)

        return
    
    def extra_repay(self, asset):
        
        try:
            for item in self.client.get_isolated_margin_account()['assets']:
                if item['baseAsset']['asset'] == asset and item['quoteAsset']['asset'] == self.base_coin:
                    if float(item['baseAsset']['free']) > 0 and float(item['baseAsset']['borrowed']) > 0:
                        self.client.repay_margin_loan(asset=asset, amount=float(item['baseAsset']['free']), symbol=asset+self.base_coin, isIsolated=True)
                    if float(item['quoteAsset']['free']) > 0 and float(item['quoteAsset']['borrowed']) > 0:
                        self.client.repay_margin_loan(asset=self.base_coin, amount=float(item['quoteAsset']['free']), symbol=asset+self.base_coin, isIsolated=True)        
                        self.notifier.register_output('Info', asset, 'general', 'Extra loan repay: ' + asset)

        except Exception as e:
            print(f"Extra repay failed: {e}")
            traceback.print_exc()
            self.notifier.register_output('Error', asset, 'general', 'Extra loan repay failed: ' + str(e))
            
        return
    
    def check_open_orders(self, time):
        
        #try:
        for i in self.open_order_list:
            order = i[0]
            symbol = i[1]
            action = i[2]            
            open_order = self.client.get_margin_order(symbol=order['symbol'], orderId=order['orderId'], isIsolated='TRUE')
            self.notifier.register_output('Check Order', symbol.asset, symbol.side, open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
            print('Check Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
            
            if open_order['status'] == 'FILLED':
                executed_amount, notional_amount, price = np.array([]), np.array([]), np.array([])
                for trade in self.client.get_margin_trades(symbol=order['symbol'], isIsolated=True):
                    if trade['orderId'] == order['orderId']:
                        executed_amount = np.append(executed_amount, [float(trade['qty'])])
                        notional_amount = np.append(notional_amount, [float(trade['quoteQty'])])
                        price = np.append(price, [float(trade['price'])])
                        date0 = str(trade['time'])[:-3]
                        date = datetime.fromtimestamp(int(date0))
                        if trade['commissionAsset'] == self.base_coin:
                            comision = float(trade['commission'])
                            symbol.commission = symbol.commission + comision
                        else:
                            comision = float(trade['commission']) * float(self.client.get_symbol_ticker(symbol=trade['commissionAsset']+self.base_coin)['price'])
                            symbol.commission = symbol.commission + comision

                total_amount = sum(executed_amount)
                average_price = np.dot(price, executed_amount)/total_amount
                self.notifier.register_output('Action', symbol.asset, symbol.side, 'Order Filled ' + str(open_order['orderId']))
                print('Order Filled ', open_order['status'] + str(open_order['orderId']))

                for i in self.open_order_list:
                    if i[0]['orderId'] == open_order['orderId']:
                        self.open_order_list.remove(i)
                self.notifier.register_output('Action', symbol.asset, symbol.side, 'Delete Open Order ' + action + ' ' + str(open_order['orderId']))
                print('Delete Open Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                
                if action == 'OPEN':
                    symbol.open_order(date, average_price, total_amount, comision)
                elif action == 'AVERAGE':
                    symbol.average_order(date, average_price, total_amount, comision)
                elif action == 'CLOSE':
                    symbol.close_order(date, average_price, total_amount, comision)
            
            elif open_order['status'] == 'PARTIALLY_FILLED':
                
                executed_amount, notional_amount, price = np.array([]), np.array([]), np.array([])
                for trade in self.client.get_margin_trades(symbol=order['symbol'], isIsolated=True):
                    if trade['orderId'] == order['orderId']:
                        executed_amount = np.append(executed_amount, [float(trade['qty'])])
                        notional_amount = np.append(notional_amount, [float(trade['quoteQty'])])
                        price = np.append(price, [float(trade['price'])])
                        date0 = str(trade['time'])[:-3]
                        date = datetime.fromtimestamp(int(date0))
                        if trade['commissionAsset'] == self.base_coin:
                            comision = float(trade['commission'])
                            symbol.commission = symbol.commission + comision
                        else:
                            comision = float(trade['commission']) * float(self.client.get_symbol_ticker(symbol=trade['commissionAsset']+self.base_coin)['price'])
                            symbol.commission = symbol.commission + comision
                            
                total_amount = sum(executed_amount)
                average_price = np.dot(price, executed_amount)/total_amount
                new_row = self.notifier.tables['open_orders'](Date=str(time), Name=symbol.name, Order_id=str(open_order['orderId']), Status=open_order['status'], Symbol=symbol.tic, Side=order['side'], Price=average_price, Amount=open_order['origQty'], Filled=total_amount, Timer=symbol.timer)
                sql_session.add(new_row)
                try:
                    sql_session.commit()
                except exc.OperationalError as e:
                    print(f"Error de conexión a la base de datos: {e}")
                    sql_session.rollback()
                symbol.timer = symbol.timer + 1
                self.notifier.register_output('Action', symbol.asset, symbol.side, 'Order Partially Filled ' + str(open_order['orderId']))
                print('Order Partially Filled ', open_order['status'] + str(open_order['orderId']))
                self.notifier.register_output('Check Partial Order', symbol.asset, symbol.side, ' Filled Amount: ' + str(total_amount) + ' Timer: ' + str(symbol.timer))
                print('Check Partial Order', 'Filled Amount: ' + str(total_amount) + ' Timer: ' + str(symbol.timer))

                if symbol.timer > 5:
                    cancel_order = self.client.cancel_margin_order(symbol=symbol.tic, orderId=order['orderId'], isIsolated='TRUE')
                    self.notifier.send_cancel_order(symbol.asset, symbol.side, action, str(open_order['orderId']))
                    self.notifier.register_output('Cancel Order', symbol.asset, symbol.side, open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    print('Cancel Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    for i in self.open_order_list:
                        if i[0]['orderId'] == open_order['orderId']:
                            self.open_order_list.remove(i)       
                    symbol.timer = 0
                    self.notifier.register_output('Action', symbol.asset, symbol.side, 'Delete Open Order ' + action + ' ' + str(open_order['orderId']))
                    print('Delete Open Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    
                    if action == 'OPEN':
                        symbol.open_order(date, average_price, total_amount, comision)
                    elif action == 'AVERAGE':
                        symbol.average_order(date, average_price, total_amount, comision)
                    elif action == 'CLOSE':
                        symbol.close_order(date, average_price, total_amount, comision)
                        
            elif open_order['status'] == 'CANCELED':
                for i in self.open_order_list:
                    if i[0]['orderId'] == open_order['orderId']:
                        self.open_order_list.remove(i)      
            else:
                self.notifier.register_output('Check Order', symbol.asset, symbol.side, open_order['status'] + str(open_order['orderId']))
                #print('Check Order', open_order['status'] + str(open_order['orderId']))
                
                new_row = self.notifier.tables['open_orders'](Date=str(time), Name=symbol.name, Order_id=str(open_order['orderId']), Status=open_order['status'], Symbol=symbol.tic, Side=order['side'], Price=open_order['price'], Amount=open_order['origQty'], Filled=open_order['executedQty'], Timer=symbol.timer)
                sql_session.add(new_row)
                try:
                    sql_session.commit()
                except exc.OperationalError as e:
                    print(f"Error de conexión a la base de datos: {e}")
                    sql_session.rollback()  # Revertir cambios pendientes, si los hay                
                symbol.timer = symbol.timer + 1

                if symbol.timer > 5:
                    self.client.cancel_margin_order(symbol=symbol.tic, orderId=open_order['orderId'], isIsolated='TRUE')
                    self.notifier.send_cancel_order(symbol.asset, symbol.side, action, str(open_order['orderId']))
                    self.notifier.register_output('Cancel Order', symbol.asset, symbol.side, open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    print('Cancel Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    symbol.timer = 0
                    for i in self.open_order_list:
                        if i[0]['orderId'] == open_order['orderId']:
                            self.open_order_list.remove(i)   
                    self.notifier.register_output('Action', symbol.asset, symbol.side, 'Delete Open Order ' + action + ' ' + str(open_order['orderId']))
                    print('Delete Open Order', open_order['symbol'] + symbol.side + action + str(open_order['orderId']))
                    
                    if action == 'OPEN':
                        symbol.can_open = True
                    elif action == 'AVERAGE':
                        symbol.can_average = True
                    elif action == 'CLOSE':
                        symbol.can_close = True
                        
        #except Exception as e:
            #print(f"Check Order Failed: {e}")
            #self.notifier.register_output('Error', 'Check Order Failed: ' + str(e))
        self.notifier.register_output('Info', 'general', 'general', 'Orders Checked')

        return
    
    def create_buy_order(self, symbol, buy_amount, price, action):
        
        order_qty = self.round_decimals_up(max(buy_amount, self.initial_amount/price), self.amount_precision[symbol.asset])
        order_price = round(price, self.price_precision[symbol.asset])

        self.get_asset_balances(symbol.asset, self.amount_precision[symbol.asset])
        self.get_base_balances(symbol.asset)
        
        if self.balances[self.base_coin] < order_qty * price:
            loan = max(order_qty * price - self.balances[self.base_coin], self.initial_amount) + 1
            self.create_loan(loan, 2, self.base_coin, symbol)       
            self.get_asset_balances(symbol.asset, self.amount_precision[symbol.asset])
            self.get_base_balances(symbol.asset)
        
        if self.balances[self.base_coin] >= order_qty * price:
            time = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second)
            try:
                buy_open_order = self.client.create_margin_order(symbol=symbol.tic, side='BUY', type='LIMIT', timeInForce='GTC', quantity=order_qty, price=order_price, isIsolated='TRUE')
                print('Buy Order Placed', symbol.name, 'price: ', round(price,2), 'amount: ', order_qty)
                # self.notifier.send_order_placed(price, order_qty, symbol, action, buy_open_order['orderId'], self.balances[self.base_coin], self.balances[symbol.asset])
                self.open_order_list.append([buy_open_order, symbol, action])
                filled = 0
                for i in buy_open_order['fills']:
                    filled = filled + float(i['qty'])
                new_row = self.notifier.tables['open_orders'](Date=str(time), Name=symbol.name, Order_id=str(buy_open_order['orderId']), Status=buy_open_order['status'], Symbol=symbol.tic, Side='BUY', Price=buy_open_order['price'], Amount=buy_open_order['origQty'], Filled=filled, Timer=symbol.timer)
                sql_session.add(new_row)
                try:
                    sql_session.commit()
                except exc.OperationalError as e:
                    print(f"Error de conexión a la base de datos: {e}")
                    sql_session.rollback()  # Revertir cambios pendientes, si los hay
                
                if action == 'OPEN': 
                    symbol.can_open_trail = False
                elif action == 'AVERAGE':
                    symbol.can_average_trail = False
                elif action == 'CLOSE':
                    symbol.can_close_trail = False
            except Exception as e:
                traceback.print_exc()
                self.notifier.register_output('Error', symbol.asset, symbol.side, 'Buy Order Creation Failed: ' + str(e))
        return
    
    def create_sell_order(self, symbol, buy_amount, price, action):
        
        order_qty = self.round_decimals_down(max(buy_amount, self.initial_amount/price), self.amount_precision[symbol.asset])
        order_price = round(price, self.price_precision[symbol.asset])

        self.get_asset_balances(symbol.asset, self.amount_precision[symbol.asset])
        self.get_base_balances(symbol.asset)
        
        if self.balances[symbol.asset] < order_qty:
            loan = max(order_qty - self.balances[symbol.asset], self.initial_amount/price) + 1/price
            self.create_loan(loan, self.amount_precision[symbol.asset], symbol.asset, symbol)
            self.get_asset_balances(symbol.asset, self.amount_precision[symbol.asset])
            self.get_base_balances(symbol.asset)
        
        if self.balances[symbol.asset] >= order_qty:
            time = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second)
            try:
                sell_open_order = self.client.create_margin_order(symbol=symbol.tic, side='SELL', type='LIMIT', timeInForce='GTC', quantity=order_qty, price=order_price, isIsolated='TRUE')
                print('Sell Order Placed', symbol.name, 'price: ', round(price,2), 'amount: ', order_qty)
                # self.notifier.send_order_placed(price, order_qty, symbol, action, sell_open_order['orderId'], self.balances[self.base_coin], self.balances[symbol.asset])
                self.open_order_list.append([sell_open_order, symbol, action])
                filled = 0
                for i in sell_open_order['fills']:
                    filled = filled + float(i['qty'])
                new_row = self.notifier.tables['open_orders'](Date=str(time), Name=symbol.name, Order_id=str(sell_open_order['orderId']), Status=sell_open_order['status'], Symbol=symbol.tic, Side='SELL', Price=sell_open_order['price'], Amount=sell_open_order['origQty'], Filled=filled, Timer=symbol.timer)
                sql_session.add(new_row)
                try:
                    sql_session.commit()
                except exc.OperationalError as e:
                    print(f"Error de conexión a la base de datos: {e}")
                    sql_session.rollback()  # Revertir cambios pendientes, si los hay
                
                if action == 'OPEN':
                    symbol.can_open_trail = False
                elif action == 'AVERAGE':
                    symbol.can_average_trail = False
                elif action == 'CLOSE':
                    symbol.can_close_trail = False
            except Exception as e:
                traceback.print_exc()
                self.notifier.register_output('Error', symbol.asset, symbol.side, 'Sell Order Creation Failed: ' + str(e))
        return
    
    def calculate_nav(self, time):
        try:
            asset_value = self.balances[self.base_coin]
            liabilities = self.loans[self.base_coin]
            self.nav = self.balances[self.base_coin] - self.loans[self.base_coin]
            for asset in self.assets:
                price = float(self.client.get_symbol_ticker(symbol=asset+self.base_coin)['price'])
                asset_value = asset_value + self.balances[asset]*price
                liabilities = liabilities + self.loans[asset]*price
                self.nav = self.nav + self.balances[asset]*price - self.loans[asset]*price
            
            if liabilities == 0 or asset_value/liabilities > 999:
                self.margin = 999
            else:
                self.margin = asset_value/liabilities
            
            margin_account = self.client.get_isolated_margin_account()
            if float(margin_account['totalLiabilityOfBtc']) == 0:
                margin = 999
            else:
                margin  = float(margin_account['totalAssetOfBtc'])/float(margin_account['totalLiabilityOfBtc'])
                #self.bnb_margin_list.append(margin)
            btc_price = float(self.client.get_symbol_ticker(symbol='BTCUSDT')['price'])
            #self.bnb_nav_list.append(float(margin_account['totalNetAssetOfBtc'])*btc_price)
            
            new_row = self.notifier.tables['nav'](Date=str(time), Nav=self.nav, Bnb_nav=float(margin_account['totalNetAssetOfBtc'])*btc_price)
            sql_session.add(new_row)
            new_row = self.notifier.tables['margin'](Date=str(time), Margin=margin)
            
            sql_session.add(new_row)
            try:
                sql_session.commit()
            except exc.OperationalError as e:
                print(f"Error de conexión a la base de datos: {e}")
                sql_session.rollback()  # Revertir cambios pendientes, si los hay
            self.notifier.register_output('Info', 'general', 'general', 'Nav calculated')
            
        except Exception as e:
            print(f"Nav calculating error: {e}")
            self.notifier.register_output('Error', 'general', 'general', 'Nav calculating error: ' + str(e))
        return       
    
    
__all__ = ['Margin_account']
