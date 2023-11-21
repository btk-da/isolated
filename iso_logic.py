# -*- coding: utf-8 -*-
"""
Created on Fri Sep  8 17:09:12 2023

@author: gorka
"""

#LOGIC

import socket
import time
import requests
import pickle
import copy
from binance.exceptions import BinanceAPIException
from bot_symbol_combi import Symbol_combi
from bot_symbol_long import Symbol_long
from bot_symbol_short import Symbol_short
from bot_notifier import Notifier
from bot_account import Margin_account
from bot_database import init_database, sql_assets, sql_session
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError


url = 'https://api.telegram.org/bot6332743294:AAFKcqzyfKzXAPSGhR6eTKLPMyx0tpCzeA4/sendMessage'

# inputs = [{'drop': 1, 'profit': 0.5, 'k': 1.2, 'buy_trail':0.25, 'sell_trail':0.15, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'},
#           {'drop': -1, 'profit': 0.5, 'k': 1.2, 'buy_trail':0.15, 'sell_trail':0.25, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'}]

inputs = [{'drop': 0.2, 'profit': 0.1, 'k': 1.2, 'buy_trail':0.05, 'sell_trail':0.05, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'},
          {'drop': -0.2, 'profit': 0.1, 'k': 1.2, 'buy_trail':0.05, 'sell_trail':0.05, 'drop_param':2.5, 'level':1, 'pond':5, 'asset': 'BTC'}]

backup = False

if __name__ == '__main__':
    
    if backup:
        
        sql_tables = init_database(sql_assets, True)
        account = Margin_account(Notifier())
        account.notifier.tables = sql_tables
        
        master = Symbol_combi()
        master.account = account
        
        with open("master.pickle", "rb") as f:
            master_back = pickle.load(f)
        
        master.symbol_list = master_back
        for i in master.symbol_list:
            i.master = master

        master.init_params(True)  
        print('Backup charged')
        
    else:
    
        sql_tables = init_database(sql_assets, False)
        account = Margin_account(Notifier())
        account.notifier.tables = sql_tables
        
        master = Symbol_combi()
        master.account = account
        master.add_symbols(inputs)
        master.init_params(False)    
        print('System initialized')
    
    print('Start Operating')
    
    while True:
        
        if master.engine_working == True:
            
            try:
                master.update_open_tr()
                backup_list = copy.deepcopy(master.symbol_list)
                
                for i in backup_list:
                    i.master = []
                with open("master.pickle", "wb") as f:
                    pickle.dump(backup_list, f)
                    
            except BinanceAPIException as e:
                print(f"Se produjo un error de la API de Binance: {e}")
                master.account.notifier.register_output('Error', 'general', 'general', 'Binance API error ' + str(e))
            except requests.exceptions.ReadTimeout as e:
                print(f"Error de tiempo de espera en la API de Binance: {e}")
                master.account.notifier.register_output('Error', 'general', 'general', 'Binance API error ' + str(e))
            except OperationalError as e:
                # Captura el error específico de SQLAlchemy
                print(f"Error de conexión a la base de datos: {e}")
            # except Exception as e:
            #     print(f"ERROR NO IDENTIFICADO: {e}")
            time.sleep(30)

            try: # Conectarse con frontend y pedir instrucciones
                logic_front_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                logic_front_socket.settimeout(5) # Esperar 5 segundos antes de ejecutar la lógica
                logic_front_socket.connect(('localhost', 5559))
                
                texto = 'Conexion success'
                mensaje = texto.encode('utf-8')
                logic_front_socket.send(mensaje)
                
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  texto, 'parse_mode': 'HTML'})
                
                logic_front_socket.close()
                
                master.engine_working = False
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine stopped', 'parse_mode': 'HTML'})

            except socket.error as e:
                pass                
            except socket.timeout:
                pass

            except Exception as e:
                print('Error de logic al conectar frontend: ', str(e))
                requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Error de logic al conectar frontend: ' + str(e), 'parse_mode': 'HTML'})
                # time.sleep(30)
            finally:
                logic_front_socket.close()

            
        elif master.engine_working == False:
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as front_server:
                front_server.bind(('localhost', 5558))
                front_server.listen(1)
                conexion, direccion = front_server.accept()
                
                try:
                    data = conexion.recv(1024)
                    texto = data.decode('utf-8')
                    requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Text received: ' + texto, 'parse_mode': 'HTML'})
                
                    # if texto == 'SWITCH':
                    if 'SWITCH' in texto:
                        switch_data = conexion.recv(1024)
                        switch_texto = switch_data.decode('utf-8')
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Change: ' + str(switch_texto), 'parse_mode': 'HTML'})
                        
                        with open("master.pickle", "rb") as f:
                            master_back = pickle.load(f)
                        master.symbol_list = master_back
                        for i in master.symbol_list:
                            i.master = master
    
                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            sql_session.add(new_row)
                        sql_session.commit()
    
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Engine started (switch)', 'parse_mode': 'HTML'})
                        conexion.close()
    
                    # elif texto == 'EDIT SYMBOL':
                    elif 'EDIT SYMBOL' in texto:
    
                        edit_symbol_data = conexion.recv(1024)
                        edit_symbol_texto = edit_symbol_data.decode('utf-8')
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'Change: ' + edit_symbol_texto, 'parse_mode': 'HTML'})

                        
                        with open("master.pickle", "rb") as f:
                            master_back = pickle.load(f)
                        master.symbol_list = master_back
                        for i in master.symbol_list:
                            i.master = master
                            i.trading_points()
                        
                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            new_row = self.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Drop_param=symbol.drop_param, Level=symbol.level, Pond=symbol.pond, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)

                            sql_session.add(new_row)
                        sql_session.commit()                    
        
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started (edit)', 'parse_mode': 'HTML'})
                        conexion.close()
    
                    # elif texto == 'ADD SYMBOL':
                    elif 'ADD SYMBOL' in texto:
    
                        add_symbol_data = conexion.recv(4096)
                        add_symbol_texto = pickle.loads(add_symbol_data)
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'New symbol data received ' + str(add_symbol_texto), 'parse_mode': 'HTML'})
                        
                        with open("master.pickle", "rb") as f:
                            master_back = pickle.load(f)
                        master.symbol_list = master_back
                        for i in master.symbol_list:
                            i.master = master
                        
                        master.add_new_symbol(add_symbol_texto)
    
                        restart_symbols = delete(master.account.notifier.tables['symbols'])
                        sql_session.execute(restart_symbols)
                        for symbol in master.symbol_list:
                            new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                            sql_session.add(new_row)
                        sql_session.commit()      
    
                        requests.post(url, data={'chat_id': '-1001802125737', 'text': 'New symbol added', 'parse_mode': 'HTML'})
                        master.engine_working = True
                        requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started (add)', 'parse_mode': 'HTML'})
                        conexion.close()

                except socket.error:
                    pass
                except socket.timeout:
                    pass
                
                finally:
                    conexion.close()


            # except Exception as e:
            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'ERROR: Master not received: ' + str(e), 'parse_mode': 'HTML'})
            #     master.engine_working = True
            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine restarted', 'parse_mode': 'HTML'})

                
                
                # elif texto == 'Hey logic, sigue con lo tuyo':
                
                    # restart_symbols = delete(master.account.notifier.tables['symbols'])
                    # sql_session.execute(restart_symbols)
                    
                    # with open("master.pickle", "rb") as f:
                    #     master_back = pickle.load(f)
                    
                    # master.symbol_list = master_back
                    # for i in master.symbol_list:
                    #     i.master = master
                    #     i.trading_points()
                    
                    # for symbol in master.symbol_list:
                    #     new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
                    #     sql_session.add(new_row)
                    
                    # sql_session.commit()
                
                    # requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Master received: ' + str(texto), 'parse_mode': 'HTML'})
                    # conexion.close()
                    # front_server.close()
                    # if conexion._closed and front_server._closed:
                    #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Logic socket closed', 'parse_mode': 'HTML'})
                    # else:
                    #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'ERROR: Logic socket not closed', 'parse_mode': 'HTML'})
    
                    # master.engine_working = True
                    # requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started', 'parse_mode': 'HTML'})
            
            
            # try:
            #     # Crear servidor y esperar a que el frontend envíe instrucciones
            #     front_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #     front_server.bind(('localhost', 5558))
            #     front_server.listen(1)
            #     front_server.settimeout(5)
            #     conexion, direccion = front_server.accept()
            #     data = conexion.recv(4096)
            #     received_inputs = pickle.loads(data)

            #     with open("master.pickle", "rb") as f:
            #         master_back = pickle.load(f)

            #     master.symbol_list = master_back
            #     for i in master.symbol_list:
            #         i.master = master

            #     master.add_new_symbol(received_inputs)

            #     restart_symbols = delete(master.account.notifier.tables['symbols'])
            #     sql_session.execute(restart_symbols)

            #     for symbol in master.symbol_list:
            #         new_row = master.account.notifier.tables['symbols'](Name=symbol.name, Drop=symbol.drop, Profit=symbol.profit, K=symbol.k, Buy_trail=symbol.buy_trail, Sell_trail=symbol.sell_trail, Switch=symbol.switch, Symbol_status=symbol.status, Can_open=symbol.can_open, Can_average=symbol.can_average, Can_close=symbol.can_close, Can_open_trail=symbol.can_open_trail, Can_average_trail=symbol.can_average_trail, Can_close_trail=symbol.can_close_trail)
            #         sql_session.add(new_row)
                
            #     sql_session.commit()

            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Symbol added: ' + str(received_inputs), 'parse_mode': 'HTML'})
            #     master.engine_working = True
            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine started', 'parse_mode': 'HTML'})

            #     conexion.close()
            #     front_server.close()

            #     if conexion._closed and front_server._closed:
            #         pass
            #     else:
            #         requests.post(url, data={'chat_id': '-1001802125737', 'text':  'ERROR: Front socket not closed', 'parse_mode': 'HTML'})

            # except socket.error as e:
            #     # print('Error de socket: ', str(e))
            #     # requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Error de socket: ' + str(e), 'parse_mode': 'HTML'})
            #     pass

            # except socket.timeout:
            #     pass

            # except Exception as e:
            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'ERROR: Master not received: ' + str(e), 'parse_mode': 'HTML'})
            #     master.engine_working = True
            #     requests.post(url, data={'chat_id': '-1001802125737', 'text':  'Engine restarted', 'parse_mode': 'HTML'})


