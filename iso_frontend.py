# -*- coding: utf-8 -*-
"""
Created on Fri Sep  8 17:08:16 2023

@author: gorka
"""

#FRONTEND

import streamlit as st
import socket
import pickle
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import time
import numpy as np
from datetime import timedelta, datetime
import requests
from bot_symbol_combi import Symbol_combi
from bot_symbol_long import Symbol_long
from bot_symbol_short import Symbol_short
from sqlalchemy import create_engine, Column, Float, Integer, String, delete
from sqlalchemy.orm import sessionmaker, declarative_base
from bot_database import sql_session, sql_base

url = 'https://api.telegram.org/bot6332743294:AAFKcqzyfKzXAPSGhR6eTKLPMyx0tpCzeA4/sendMessage'
st.set_page_config(page_title='MARTINGALA', page_icon=':chart_with_upwards_trend:', layout='wide')


class Frontend():
    
    def __init__(self):
        
        self.symbol_list = []
        self.engine = create_engine('mysql+pymysql://server0:donoso850@localhost/eth_database')
        self.conn = self.engine.connect()
        self.symbol_names = []
        assets = ['BTC']
        for i in assets:
            self.symbol_names.append(i + '--L')
            self.symbol_names.append(i + '--S')
            
        self.symbol_names.append('ALL')
        self.logic_front = 5559
        self.front_logic = 5558

    def edit_symbol(self, new_params):

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as logic_server:
                logic_server.bind(('localhost', self.logic_front))
                logic_server.listen(1)
                conexion, direccion = logic_server.accept()
                data = conexion.recv(1024)
                texto = data.decode('utf-8')
                st.warning('Edit Symbol: ' + str(texto))
                conexion.close()

        except OSError:
            st.warning('Server occupied, try again')
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            conexion.close()

        try:
            time.sleep(5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as front_logic_socket:
                front_logic_socket.connect(('localhost', self.front_logic))
                init_message = 'EDIT SYMBOL'
                message = init_message.encode('utf-8')
                front_logic_socket.send(message)
                st.warning(init_message + ' sent')
                time.sleep(5)
                
                serialized_params = pickle.dumps(new_params)
                front_logic_socket.send(serialized_params)
                st.warning(str(new_params) + ' sent')

        except OSError as e:
            st.warning('Server occupied at return, try again : ' + str(e))
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            front_logic_socket.close()
            st.warning('Conexion closed')

        return

    def add_symbol(self, new_symbol):

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as logic_server:
                logic_server.bind(('localhost', self.logic_front))
                logic_server.listen(1)
                conexion, direccion = logic_server.accept()
                data = conexion.recv(1024)
                texto = data.decode('utf-8')
                st.warning('Add Symbol: ' + str(texto))

        except OSError:
            st.warning('Server occupied, try again')
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            conexion.close()

            
        try:    
            time.sleep(5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as front_logic_socket:
                front_logic_socket.connect(('localhost', self.front_logic))
                init_message = 'ADD SYMBOL'
                message = init_message.encode('utf-8')
                front_logic_socket.send(message)
                st.warning(init_message + ' sent')
                time.sleep(5)

                serialized_inputs = pickle.dumps(new_symbol)
                front_logic_socket.send(serialized_inputs)
                st.warning(str(new_symbol) + ' sent')

        except OSError:
            st.warning('Server occupied at return, try again')
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            front_logic_socket.close()

        return
    
    def switch_symbols(self, switch_params):
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as logic_server:
                logic_server.bind(('localhost', self.logic_front))
                logic_server.listen(1)
                conexion, direccion = logic_server.accept()
                data = conexion.recv(1024)
                texto = data.decode('utf-8')
                st.warning('Switch Symbol: ' + str(texto))
                conexion.close()
                    
        except OSError as e:
            st.warning('Server occupied, try again' + str(e))
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            conexion.close()

        try:
            time.sleep(5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as front_logic_socket:
                front_logic_socket.connect(('localhost', self.front_logic))
                init_message = 'SWITCH'
                message = init_message.encode('utf-8')
                front_logic_socket.send(message)
                st.warning(init_message + ' sent')
                time.sleep(5)
                
                serialized_switch = pickle.dumps(switch_params)
                front_logic_socket.send(serialized_switch)
                st.warning(str(switch_params) + ' sent')
                
        except OSError as e:
            st.warning('Server occupied at return, try again : ' + str(e))
        except Exception as e:
            st.warning('ERROR: ' + str(e))
        finally:
            front_logic_socket.close()
            st.warning('Conection closed')

        return 
    
    def open_tr_page(self):
  
        st.write("<h3 style='text-align: center;'>OPEN TRANSACTIONS</h3>", unsafe_allow_html=True)
    
        df0 = pd.read_sql_table('open_tr', self.conn, parse_dates=['Date'])
        df_otr = pd.DataFrame()
        df_otr['Date'] = df0['Date']
        df_otr['Name'] = df0['Name']
        df_otr['BuyLevel'] = df0['BuyLevel']
        df_otr['Amount'] = df0['Amount']
        df_otr['Cost'] = df0['Cost']
        df_otr['Profit'] = df0['Profit']
        df_otr['ProfitUsd'] = df0['ProfitUsd']
        df_otr['Duration'] = df0['Duration']
        df_otr['Date'] = df_otr['Date'].dt.strftime('%d/%m %H:%M:%S')
        df_otr = df_otr.sort_values('Cost', ascending=False)
        
        
        # Crear la tabla de Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df_otr.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[df_otr[col] for col in df_otr.columns],
                       fill_color='lavender',
                       align='left'))])
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family='Arial', size=12, color='black'),
            showlegend=False,
            title={'text': 'Transactions'},  # Posición del título centrado encima de la tabla
            width=1200,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
            height=200  # Altura de la tabla, puedes ajustarlo según tus necesidades
        )
        
        # Mostrar la tabla en el dashboard de Streamlit
        st.plotly_chart(fig)
                 
        # asset, dates, assets, amounts, costs, profits = [], [], [], [], [], []
        # amount, cost, profit = 0, 0, 0
        
        # for index, row in df_otr.iterrows():
            
        #     if row['Name'][:3] == asset:
        #         if row['Name'][-2:-1] == 'L':
        #             amount = amount + row['Amount']
        #             cost = cost + row['Cost']
        #         elif row['Name'][-2:-1] == 'S':
        #             amount = amount - row['Amount']
        #             cost = cost - row['Cost']
        #         profit = profit + row['ProfitUsd']
    
        #     else:
        #         asset = row['Name'][:3]
        #         assets.append(row['Name'][:3])
        #         amounts.append(round(amount, 4))
        #         amount = row['Amount']
        #         costs.append(cost)
        #         cost = row['Cost']
        #         profits.append(profit)
        #         profit = row['ProfitUsd']
        
        # amounts.append(amount)
        # costs.append(cost)
        # profits.append(profit)
    
        # for i in range(len(assets)):
        #     dates.append(row['Date'])
                
        # asset_df = pd.DataFrame()
        # asset_df['Date'] = dates
        # asset_df['Assets'] = assets
        # asset_df['Amount'] = amounts[1:]
        # asset_df['Cost'] = costs[1:]
        # asset_df['ProfitUsd'] = [round(number, 2) for number in profits[1:]]

        # # try:
        # #     asset_df['Margin'] = [btc_margin, eth_margin, bnb_margin, ada_margin, xrp_margin, ltc_margin, sol_margin, atom_margin, bch_margin, doge_margin, dot_margin, eos_margin, link_margin, trx_margin]
        # # except ValueError:
        # #     st.warning('charging, try again')
    
        # # Crear la tabla de Plotly
        # fig = go.Figure(data=[go.Table(
        #     header=dict(values=list(asset_df.columns),
        #                 fill_color='paleturquoise',
        #                 align='left'),
        #     cells=dict(values=[asset_df[col] for col in asset_df.columns],
        #                fill_color='lavender',
        #                align='left'))])
        
        # fig.update_layout(
        #     margin=dict(l=0, r=0, t=0, b=0),
        #     paper_bgcolor='white',
        #     plot_bgcolor='white',
        #     font=dict(family='Arial', size=12, color='black'),
        #     showlegend=False,
        #     title={'text': 'Transactions'},  # Posición del título centrado encima de la tabla
        #     width=1200,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
        #     height=500  # Altura de la tabla, puedes ajustarlo según tus necesidades
        # )
        
        # # Mostrar la tabla en el dashboard de Streamlit
        # st.plotly_chart(fig)
            
        return
    
    def live_page(self):
    
        sym_names = tuple(self.symbol_names)
        
        # Añade la barra selectora en el sidebar de la aplicación
        option = st.selectbox('Seleccione el activo a mostrar', sym_names[:-1])
    
        # Crear botón de actualización
        update_button = st.button("Update graph", key="update_button")
        
        if update_button: 
            # Leer datos de las órdenes y filtrar por compras y ventas
            df_orders = pd.read_sql_table('orders', self.conn, parse_dates=['Date'])
            df_buys = pd.DataFrame()
            df_sells = pd.DataFrame()
            df_buys = df_orders[df_orders['Type'] == 'Buy']
            df_sells = df_orders[df_orders['Type'] == 'Sell']
            df_points = pd.read_sql_table('status', self.conn)
            
            crypto_tables = {}
            for name in sym_names:
                for i in range(3):
                    crypto_tables[f'{name}'] = name[:-3]
                    crypto_tables[f'{name}'] = name[:-3]
        
            # Obtiene el nombre de la tabla a partir de la opción seleccionada
            table_name = crypto_tables[option]
            # Lee el DataFrame correspondiente a la tabla
            df_prices = pd.read_sql_table(table_name, self.conn, parse_dates=['Date'])
            
            # Filtra los DataFrames según el nombre de la criptomoneda
            df_buys = df_buys[df_buys['Name'] == option]
            df_sells = df_sells[df_sells['Name'] == option]
            action_points = df_points[df_points['Name'] == option]
            
            # Crear gráfico de líneas con los datos del histórico de BTC
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_prices['Date'], y=df_prices['Price'], mode='lines', name='Price'))
            
            # Agregar marcadores de compras y ventas
            fig.add_trace(go.Scatter(x=df_buys['Date'], y=df_buys['Price'], mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'), name='Buy', text=df_buys['Asset']))
            fig.add_trace(go.Scatter(x=df_sells['Date'], y=df_sells['Price'], mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'), name='Sell', text=df_sells['Asset']))
            
            # Personalizar diseño del gráfico
            fig.update_layout(xaxis=dict(title='Date'), yaxis=dict(title='Price'), width=1000, height=600)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=100, b=100, l=100, r=155))
            
            df_symbols = pd.read_sql_table('symbols', self.conn)
            
            points = [list(action_points['Open_point']), list(action_points['Open_trail_point']), list(action_points['Average_price']), list(action_points['Average_point']), list(action_points['Average_trail_point']), list(action_points['Close_point']), list(action_points['Close_trail_point'])]
            
            # Agregar líneas horizontales para buy_point, average_price y sell_point
            # try:
            annotations = []
            if int(df_symbols[df_symbols['Name'] == option]['Can_open'].iloc[0]) == 1 or int(df_symbols[df_symbols['Name'] == option]['Can_open_trail'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[0][0], points[0][0]], mode='lines', line=dict(color='rgba(0, 128, 0, 0.4)', width=2, dash='dash'), name='Open Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[0][0], xanchor='left', yanchor='middle', text='Open Point : ' + str(points[0][0]), showarrow=False, font=dict(color='green')))
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[1][0], points[1][0]], mode='lines', line=dict(color='rgba(0, 128, 0, 0.4)', width=2, dash='dash'), name='Open Trail Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[1][0], xanchor='left', yanchor='middle', text='Open Trail Point : ' + str(points[1][0]), showarrow=False, font=dict(color='green')))
                
            if int(df_symbols[df_symbols['Name'] == option]['Symbol_status'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[2][0], points[2][0]], mode='lines', line=dict(color='rgba(0, 0, 255, 0.3)', width=2, dash='dash'), name='Average Price'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[2][0], xanchor='left', yanchor='middle', text='Average Price : ' + str(points[2][0]), showarrow=False, font=dict(color='blue')))

            if int(df_symbols[df_symbols['Name'] == option]['Can_average'].iloc[0]) == 1 or int(df_symbols[df_symbols['Name'] == option]['Can_average_trail'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[3][0], points[3][0]], mode='lines', line=dict(color='rgba(0, 128, 0, 0.4)', width=2, dash='dash'), name='Average Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[3][0], xanchor='left', yanchor='middle', text='Average Point : ' + str(points[3][0]), showarrow=False, font=dict(color='green')))

            if int(df_symbols[df_symbols['Name'] == option]['Can_close'].iloc[0]) == 1 or int(df_symbols[df_symbols['Name'] == option]['Can_close_trail'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[5][0], points[5][0]], mode='lines', line=dict(color='rgba(255, 0, 0, 0.4)', width=2, dash='dash'), name='Close Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[5][0], xanchor='left', yanchor='middle', text='Close Point : ' + str(points[5][0]), showarrow=False, font=dict(color='red')))
            
            if int(df_symbols[df_symbols['Name'] == option]['Can_average_trail'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[4][0], points[4][0]], mode='lines', line=dict(color='rgba(144, 238, 144, 0.4)', width=2, dash='dash'), name='Average Trail Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[4][0], xanchor='left', yanchor='middle', text='Average Trail Point : ' + str(points[4][0]), showarrow=False, font=dict(color='yellow')))
            
            if int(df_symbols[df_symbols['Name'] == option]['Can_close_trail'].iloc[0]) == 1:
                fig.add_trace(go.Scatter(x=[df_prices['Date'].min(), df_prices['Date'].max()], y=[points[6][0], points[6][0]], mode='lines', line=dict(color='rgba(255, 165, 0, 0.4)', width=2, dash='dash'), name='Close Trail Point'))
                annotations.append(dict(xref='paper', yref='y', x=1.01, y=points[6][0], xanchor='left', yanchor='middle', text='Close Trail Point : ' + str(points[6][0]), showarrow=False, font=dict(color='orange')))
            
            fig.update_layout(annotations=annotations)
            st.plotly_chart(fig)
            
            # TABLA STATUS
            df_status = pd.read_sql_table('status', self.conn, parse_dates=['Date'])
            del df_status['id']
            
            df_status = df_status[df_status['Name'] == option]

            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df_status.columns),
                            fill_color='paleturquoise',
                            align='left'),
                cells=dict(values=[df_status[col] for col in df_status.columns],
                           fill_color='lavender',
                           align='left'))])
            
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='white',
                plot_bgcolor='white',
                font=dict(family='Arial', size=12, color='black'),
                showlegend=False,
                title={'text': 'Transacciones'},
                width=1000,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
                height=200  # Altura de la tabla, puedes ajustarlo según tus necesidades
            )
            
            # Mostrar la tabla en el dashboard de Streamlit
            st.plotly_chart(fig)

        return
    
    def symbols_page(self):
        
        # TABLA SYMBOLS

        df_symbols = pd.read_sql_table('symbols', self.conn)
        del df_symbols['id']
        
        # Crear la tabla de Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df_symbols.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[df_symbols[col] for col in df_symbols.columns],
                       fill_color='lavender',
                       align='left'))])
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family='Arial', size=12, color='black'),
            showlegend=False,
            title={'text': 'Symbols'},
            width=1000,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
            height=200  # Altura de la tabla, puedes ajustarlo según tus necesidades
        )
        
        st.plotly_chart(fig)
        
        # SWITCH SYMBOLS
        symbol_side = st.selectbox("Select Symbol", ['All', 'Long', 'Short'])
        switch_mode = st.selectbox("Select Mode", ['ON', 'OFF'])
        switch_params = {'side':symbol_side, 'mode':switch_mode}
        with st.form("switch_form"):
            st.form_submit_button(label='SWITCH SYMBOLS', on_click=self.switch_symbols, args=(switch_params,))
        
        # EDIT SYMBOLS
        symbol_n = st.selectbox("Select Symbol", self.symbol_names)
        param = st.selectbox("Select Parameter", ['Switch', 'Engine', 'Drop', 'TP', 'K', 'Buy Trail', 'Sell Trail', 'Drop Param', 'Level', 'Pond',
                                                  'Status', 'Can Open', 'Can Average', 'Can Close', 'Can Open Trail', 'Can Average Trail', 'Can Close Trail'])
        new_value = st.number_input(str(param))
        new_params ={'name': symbol_n, 'attribute': param, 'value': new_value}
        
        with st.form("edit_form"):
            st.form_submit_button(label="EDIT SYMBOL", on_click=self.edit_symbol, args=(new_params,))

        # ADD SYMBOLS
        drop = st.number_input('drop', value=1)
        profit = st.number_input('profit', value=0.5)
        k = st.number_input('k', value=1.2)
        buy_trail = st.number_input('buy trail', value=0.25)
        sell_trail = st.number_input('sell trail', value=0.15)
        drop_param = st.number_input('drop param', value=2.5)
        level = st.number_input('level', value=1)
        pond = st.number_input('pond', value=5)
        asset = st.text_input('asset')
        inputs = [{'drop': drop, 'profit': profit, 'k': k, 'buy_trail':buy_trail, 'sell_trail':sell_trail, 'drop_param':drop_param, 'level':level, 'pond':pond, 'asset': asset},
                  {'drop': -drop, 'profit': profit, 'k': k, 'buy_trail':sell_trail, 'sell_trail':buy_trail, 'drop_param':drop_param, 'level':level, 'pond':pond, 'asset': asset}]
        
        with st.form("add_form"):
            st.form_submit_button(label="ADD SYMBOL", on_click=self.add_symbol, args=(inputs,))
         
        return
        
    def transactions_page(self):

        # TABLA TRANSACTIONS
        df_tr = pd.read_sql_table('transactions', self.conn, parse_dates=['Date'])
        df_tr = df_tr.sort_values(by='Date', ascending=True)  
        df_tr['Date'] = df_tr['Date'].dt.strftime('%d/%m %H:%M:%S')
        
        st.write("<h3 style='text-align: center;'>EQUITY</h3>", unsafe_allow_html=True)
        
        if df_tr.size > 0:
                    
            # GRÁFICA EQUITY
            
            df_eq = pd.DataFrame()
            df_eq['Date'] = df_tr['Date']
            df_eq['Equity'] = np.cumsum(df_tr['ProfitUsd'])
            
            # Crear gráfico de líneas con los datos del histórico de BTC
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_eq['Date'], y=df_eq['Equity'], mode='lines', name='Equity'))
            
            # Personalizar diseño del gráfico
            fig.update_layout(xaxis=dict(title='Date'),
                              yaxis=dict(title='USDT'),
                              width=1000, height=600)
            
            # Mostrar gráfico en Streamlit
            st.plotly_chart(fig)
            
        st.write("<h3 style='text-align: center;'>TRANSACTIONS</h3>", unsafe_allow_html=True)
    
        def timedelta_to_hours(td):
            return td.total_seconds() / 3600
        
        # Función para convertir y agregar la columna Duration en horas
        def convert_and_aggregate_duration(df):
            df['Duration'] = pd.to_timedelta(df['Duration'])
            df['Duration'] = df['Duration'].apply(timedelta_to_hours)
            return df
       
        # Aplicar la función convert_and_aggregate_duration para convertir y calcular el promedio de Duration en horas
        df_tr1 = convert_and_aggregate_duration(df_tr)
        
        # Definir funciones de agregación
        aggregation_functions = {
            'BuyLevel': lambda x: round(x.mean(), 1),
            'Cost': lambda x: round(x.mean(), 2),
            'Profit': lambda x: round(x.mean(), 2),
            'ProfitUsd': lambda x: round(x.sum(), 2),
            'Duration': lambda x: round(x.mean(), 2)
        }
        
        now = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, datetime.now().second) - timedelta(minutes=3)
        period = (now - datetime(2023, 11, 9, 21, 0, 0)).total_seconds()/86400
        #ACTUALIZAR AL INICIO
        
        df_aggregated = df_tr1.groupby('Name').agg(aggregation_functions).reset_index()
        df_aggregated['Rent'] = ((1 + df_aggregated['ProfitUsd']/8500) ** (1/(period/365)) - 1) * 100
        df_aggregated['Rent'] = df_aggregated['Rent'].round(2)
        name_counts = df_tr1['Name'].value_counts().reindex(df_aggregated['Name']).fillna(0).astype(int)
        df_aggregated['Num Ops'] = name_counts.reset_index(drop=True)
        df_aggregated = df_aggregated.sort_values(by='Rent', ascending=False)
        new_column_order = ['Name', 'Rent', 'Num Ops', 'ProfitUsd', 'Duration', 'Profit', 'BuyLevel', 'Cost']
        df_aggregated = df_aggregated[new_column_order]
        
        df_aggregated = df_aggregated.rename(columns={
        'Rent': 'Rent Anual',
        'ProfitUsd': 'Profit (Total $)',
        'Duration': 'Duration (Average Hours)',
        'Profit': 'Profit (Average %)',
        'Cost': 'Cost (Average $)',
        'BuyLevel': 'Buy Level (Average)'
        })
        
        df_tr0 = pd.read_sql_table('transactions', self.conn, parse_dates=['Date'])
        aggregation_functions = {'Cost': lambda x: round(x.max(), 2)}
        df_aggregated0 = df_tr0.groupby('Name').agg(aggregation_functions).reset_index()
        df_aggregated['Max Acc ($)'] = df_aggregated0['Cost']
    
        grouped = {'Name':'TOTAL', 'Rent Anual':round(((1 + sum(df_tr['ProfitUsd'])/8500) ** (1/(period/365)) - 1) * 100, 2),
                   'Num Ops':len(df_tr['ProfitUsd']), 'Profit (Total $)':round(sum(df_tr['ProfitUsd']),2),
                   'Duration (Average Hours)':np.around(np.mean(df_tr['Duration']),2), 'Profit (Average %)':np.around(np.mean(df_tr['Profit']),2),
                   'Cost (Average $)':np.around(np.mean(df_tr['Cost']),2), 'Buy Level (Average)':np.around(np.mean(df_tr['BuyLevel']),1),
                   'Max Acc ($)':max(df_aggregated0['Cost'])}
        df_total = pd.DataFrame([grouped])
        df_aggregated = pd.concat([df_aggregated, df_total], ignore_index=True)
        
    
        # Crear la tabla de Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df_aggregated.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[df_aggregated[col] for col in df_aggregated.columns],
                       fill_color='lavender',
                       align='left'))])
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family='Arial', size=12, color='black'),
            showlegend=False,
            title={'text': 'Transacciones'},
            width=1000,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
            height=900  # Altura de la tabla, puedes ajustarlo según tus necesidades
        )
        
        st.plotly_chart(fig)
        
        df_tr = df_tr.sort_values(by='id', ascending=False)  
        df_tr = df_tr.head(10)
        df_tr['Profit'] = df_tr['Profit'].round(2)
        df_tr['ProfitUsd'] = df_tr['ProfitUsd'].round(2)
        df_tr['Commission'] = df_tr['Commission'].round(2)
        df_tr['Duration'] = df_tr['Duration'].round(2)
    
        # Crear la tabla de Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df_tr.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[df_tr[col] for col in df_tr.columns],
                       fill_color='lavender',
                       align='left'))])
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family='Arial', size=12, color='black'),
            showlegend=False,
            title={'text': 'Transacciones'},
            width=1000,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
            height=200  # Altura de la tabla, puedes ajustarlo según tus necesidades
        )
        
        # Mostrar la tabla en el dashboard de Streamlit
        st.plotly_chart(fig)
        return
   
    def leverage_page(self):
    
        df_lev = pd.read_sql_table('funds', self.conn, parse_dates=['Date'])
        general_leverage = df_lev.iloc[-1]['Funds']
        long_leverage = df_lev.iloc[-1]['Long_funds']
        short_leverage = -df_lev.iloc[-1]['Short_funds']    
        
        # Creamos una figura con tres subplots en una fila
        fig_leverage = make_subplots(rows=1, cols=3, subplot_titles=("General Leverage", "Long Leverage", "Short Leverage"))
        
        # Agregamos las tres barras en los subplots correspondientes
        fig_leverage.add_trace(go.Bar(x=[0], y=[general_leverage], orientation='v', marker=dict(color='yellow'), width=0.5), row=1, col=1)
        fig_leverage.add_trace(go.Bar(x=[0], y=[long_leverage], orientation='v', marker=dict(color='green'), width=0.5), row=1, col=2)
        fig_leverage.add_trace(go.Bar(x=[0], y=[short_leverage], orientation='v', marker=dict(color='red'), width=0.5), row=1, col=3)
        
        y_range = [-100, 100]
        # Configuramos el diseño de los subplots
        for i in range(2, 4):  # Iterar sobre los tres subplots
            fig_leverage.update_yaxes(range=y_range, row=1, col=i)  # Establecer el rango en el eje y para cada subplot
            fig_leverage.update_xaxes(showticklabels=False, row=1, col=i)  # Ocultar las etiquetas del eje x
    
        # Configuramos el diseño de los subplots
        fig_leverage.update_layout(
            xaxis=dict(showticklabels=False),
            yaxis=dict(title='Leverage', range=y_range),
            showlegend=False,
            height=400,
            width=800,  # Aumentamos el ancho total para alojar las tres gráficas
            margin=dict(l=50, r=50, t=50, b=50),
            paper_bgcolor='white',
            plot_bgcolor='white',
        )
        
        # Ajustamos el tamaño del recuadro al tamaño del gráfico
        st.plotly_chart(fig_leverage, use_container_width=True)
        
        # TABLA OUTPUT
        
        st.write("<h3 style='text-align: center;'>OUTPUT</h3>", unsafe_allow_html=True)
    
        df_tr = pd.read_sql_table('output', self.conn, parse_dates=['Date'])
        df_tr = df_tr.drop(columns='id')
        df_tr = df_tr.sort_values(by='Date', ascending=False)
        df_tr['Date'] = df_tr['Date'].dt.strftime('%d/%m %H:%M:%S')
    
        # Crear la tabla de Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df_tr.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[df_tr[col] for col in df_tr.columns],
                       fill_color='lavender',
                       align='left'))])
    
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(family='Arial', size=12, color='black'),
            showlegend=False,
            title={'text': 'Output'},
            width=1400,  # Ancho de la tabla, puedes ajustarlo según tus necesidades
            height=400  # Altura de la tabla, puedes ajustarlo según tus necesidades
        )
    
        # Mostrar la tabla en el dashboard de Streamlit
        st.plotly_chart(fig)
        return
    
    def margin_page(self):
    
        #df_mar = pd.read_sql_table('margin', self.conn, parse_dates=['Date'])
        #general_margin = df_mar.iloc[-1]['Margin']
        
        #fig_leverage = go.Figure(data=[go.Bar(x=[0], y=[general_margin])])

        # fig_leverage.add_trace(go.Bar(x=[0], y=[margin_list[n]], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=n+1)

       
        # margin_list = [general_margin, btc_margin, eth_margin, bnb_margin, ada_margin, xrp_margin, ltc_margin, sol_margin, atom_margin, bch_margin, doge_margin, dot_margin, eos_margin, link_margin, trx_margin]
        
        # # Creamos una figura con tres subplots en una fila
        # fig_leverage = make_subplots(rows=1, cols=5, subplot_titles=("General Margin", "BTC Margin", "ETH Margin", "BNB Margin", "ADA Margin",
        #                                                              "XRP Margin","LTC Margin","SOL Margin","ATOM Margin","BCH Margin"
        #                                                              "DOGE Margin","DOT Margin","EOS Margin","LINK Margin","TRX Margin"))
        
        # # Agregamos las tres barras en los subplots correspondientes
        # n = 0
        # for i in margin_list:
            
        #     fig_leverage.add_trace(go.Bar(x=[0], y=[margin_list[n]], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=n+1)
        #     n = n + 1
        
        # # fig_leverage.add_trace(go.Bar(x=[0], y=[general_margin], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=1)
        # # fig_leverage.add_trace(go.Bar(x=[0], y=[btc_margin], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=2)
        # # fig_leverage.add_trace(go.Bar(x=[0], y=[eth_margin], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=3)
        # # fig_leverage.add_trace(go.Bar(x=[0], y=[bnb_margin], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=4)
        # # fig_leverage.add_trace(go.Bar(x=[0], y=[ada_margin], orientation='v', marker=dict(color='orange'), width=0.5), row=1, col=5)       
        
        # y_range = [0, 14]
        # # Configuramos el diseño de los subplots
        # for i in range(1, 6):  # Iterar sobre los tres subplots
        #     fig_leverage.update_yaxes(type='log', range=y_range, row=1, col=i)  # Establecer el rango en el eje y para cada subplot
        #     fig_leverage.update_xaxes(showticklabels=False, row=1, col=i)  # Ocultar las etiquetas del eje x
    
        # # Configuramos el diseño de los subplots
        # fig_leverage.update_layout(
        #     xaxis=dict(showticklabels=False),
        #     yaxis=dict(title='Leverage'),
        #     showlegend=False,
        #     height=400,
        #     width=800,  # Aumentamos el ancho total para alojar las tres gráficas
        #     margin=dict(l=50, r=50, t=50, b=50),
        #     paper_bgcolor='white',
        #     plot_bgcolor='white',
        # )
        
        # Ajustamos el tamaño del recuadro al tamaño del gráfico
        #st.plotly_chart(fig_leverage, use_container_width=True)
        
        
        df_nav = pd.read_sql_table('nav', self.conn, parse_dates=['Date'])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_nav['Date'], y=df_nav['Bnb_nav'], mode='lines', name='Nav'))
        
        fig.update_layout(
            title_text='NAV',
            title_x=0.5,
            title_font_size=24,
            showlegend=False,
            height=400,
            width=1000,
            margin=dict(l=50, r=50, t=50, b=50),
            paper_bgcolor='white',
            plot_bgcolor='white',
        )
        
        st.plotly_chart(fig)
        return


dashboard = Frontend()

# Barra lateral con los botones de navegación
button_1 = st.sidebar.button("OPEN TRANSACTIONS")
button_2 = st.sidebar.button("LIVE")
button_3 = st.sidebar.button("SYMBOLS")
button_4 = st.sidebar.button("TRANSACTION HISTORY")
#button_5 = st.sidebar.button("LEVERAGE")
button_6 = st.sidebar.button("NAV")

if 'button_1' not in st.session_state:
    st.session_state.button_1 = True

if 'button_2' not in st.session_state:
    st.session_state.button_2 = False

if 'button_3' not in st.session_state:
    st.session_state.button_3 = False

if 'button_4' not in st.session_state:
    st.session_state.button_4 = False

#if 'button_5' not in st.session_state:
#    st.session_state.button_5 = False

if 'button_6' not in st.session_state:
    st.session_state.button_6 = False

# if 'long_switch' not in st.session_state:
#     st.session_state.long_switch = True
# if 'short_switch' not in st.session_state:
#     st.session_state.short_switch = True


if button_6:
    st.session_state.button_6 = True
    # st.session_state.button_5 = False
    st.session_state.button_4 = False
    st.session_state.button_3 = False
    st.session_state.button_2 = False
    st.session_state.button_1 = False
# elif button_5:
#     st.session_state.button_6 = False
#     # st.session_state.button_5 = True
#     st.session_state.button_4 = False
#     st.session_state.button_3 = False
#     st.session_state.button_2 = False
#     st.session_state.button_1 = False
elif button_4:
    st.session_state.button_6 = False
    # st.session_state.button_5 = False
    st.session_state.button_4 = True
    st.session_state.button_3 = False
    st.session_state.button_2 = False
    st.session_state.button_1 = False
elif button_3:
    st.session_state.button_6 = False
    # st.session_state.button_5 = False
    st.session_state.button_4 = False
    st.session_state.button_3 = True
    st.session_state.button_2 = False
    st.session_state.button_1 = False
elif button_2:
    st.session_state.button_6 = False
    # st.session_state.button_5 = False
    st.session_state.button_4 = False
    st.session_state.button_3 = False
    st.session_state.button_2 = True
    st.session_state.button_1 = False
elif button_1:
    st.session_state.button_6 = False
    # st.session_state.button_5 = False
    st.session_state.button_4 = False
    st.session_state.button_3 = False
    st.session_state.button_2 = False
    st.session_state.button_1 = True

if st.session_state.button_6:
    dashboard.margin_page()
# elif st.session_state.button_5:
#     dashboard.leverage_page()
elif st.session_state.button_4:
    dashboard.transactions_page()
elif st.session_state.button_3:
    dashboard.symbols_page()
elif st.session_state.button_2:
    dashboard.live_page()
elif st.session_state.button_1:
    dashboard.open_tr_page()