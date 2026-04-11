import pandas as pd
import os
from .audit_logger import logger

class ExcelProcessor:
    def __init__(self, file_path='Planilha NOVA de higiene de Mãos.xlsx'):
        self.file_path = file_path
        self.df = None
        self.validations_df = None
        self.load_data()

    def load_data(self):
        if os.path.exists(self.file_path):
            try:
                # Carregar apenas VALIDAÇÕES do Excel (Listas de Unidades, etc)
                self.validations_df = pd.read_excel(self.file_path, sheet_name='VALIDAÇÕES')
                # A Tabulação Geral inicia vazia e é preenchida pelo Supabase/External Data
                self.df = pd.DataFrame(columns=[
                    'Mês (automático)', 'Ano (automático)', 'Observador', 'Unidade', 
                    'Profissional Auditado', 'Momento Auditado', 'Produto utilizado', 
                    'HM realizada?', 'Login', 'Horário'
                ])
                logger.log_system("ExcelProcessor: Estrutura inicial pronta. Aguardando dados externos.")
            except Exception as e:
                logger.log_error("EXCEL_LOAD_VALIDATIONS", str(e))

    def update_from_external_data(self, data_list):
        """
        Recebe uma lista de dicionários (Ex: do Supabase) e atualiza o DataFrame interno.
        Forçamos o reset do DF para garantir que dados antigos sumam.
        """
        # Sempre resetar o DF atual para garantir que não haja "lixo" legado
        self.df = pd.DataFrame(columns=[
            'Mês (automático)', 'Ano (automático)', 'Observador', 'Unidade', 
            'Profissional Auditado', 'Momento Auditado', 'Produto utilizado', 
            'HM realizada?', 'Login', 'Horário'
        ])
        
        if not data_list:
            logger.log_system("ExcelProcessor: Nenhum dado recebido. DF permanece vazio.", level=30) # Warning
            return

        new_df = pd.DataFrame(data_list)
        if not new_df.empty:
            self.df = new_df
            logger.log_system(f"ExcelProcessor: 100% SUPABASE SYNC - {len(self.df)} registros.")

    def get_dropdown_lists(self):
        if self.validations_df is None: return {}
        # As listas começam na linha 1 (índice 0 no pandas se não houver header)
        # Vamos pegar as colunas A e B e limpar NaNs
        return {
            "unidades": self.validations_df.iloc[:, 0].dropna().unique().tolist(),
            "categorias": self.validations_df.iloc[:, 1].dropna().unique().tolist(),
            "momentos": [
                "1 - Antes contato paciente", 
                "2 - Antes proced. asséptico", 
                "3 - Após risco exposição", 
                "4 - Após contato paciente", 
                "5 - Após contato áreas próximas"
            ],
            "insumos": ["Álcool", "Sabão", "Não Realizou"]
        }

    def get_full_stats(self):
        if self.df is None: return {"global": 0, "total_audits": 0, "moments": {}, "categories": {}}
        
        total = len(self.df)
        # Nomes Reais da Planilha NOVA
        col_hm = 'HM realizada?' if 'HM realizada?' in self.df.columns else 'HM REALIZADA?'
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        
        realizadas = len(self.df[self.df[col_hm].astype(str).str.upper() == 'SIM'])
        compliance_global = (realizadas / total * 100) if total > 0 else 0

        # Stats por Momento
        moments_stats = {}
        if col_mom in self.df.columns:
            moments_stats = self.df.groupby(col_mom)[col_hm].apply(
                lambda x: (x.astype(str).str.upper() == 'SIM').sum() / len(x) * 100 if len(x) > 0 else 0
            ).to_dict()

        # Stats por Categoria
        category_stats = {}
        if col_cat in self.df.columns:
            category_stats = self.df.groupby(col_cat)[col_hm].apply(
                lambda x: (x.astype(str).str.upper() == 'SIM').sum() / len(x) * 100 if len(x) > 0 else 0
            ).to_dict()

        return {
            "global": round(compliance_global, 1),
            "total_audits": total,
            "moments": {str(k): round(v, 1) for k, v in moments_stats.items()},
            "categories": {str(k): round(v, 1) for k, v in category_stats.items()}
        }

    def get_raw_tabulation(self):
        if self.df is None: return []
        return self.df.head(100).fillna('').to_dict(orient='records')

    def get_dashboard_data(self, unit=None, month=None, year=None):
        if self.df is None: return {}
        
        df_filtered = self.df.copy()
        col_hm = 'HM realizada?' if 'HM realizada?' in self.df.columns else 'HM REALIZADA?'
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        col_unit = 'Unidade' if 'Unidade' in self.df.columns else 'UNIDADE'
        col_month = 'Mês (automático)' if 'Mês (automático)' in self.df.columns else 'MÊS'
        col_year = 'Ano (automático)' if 'Ano (automático)' in self.df.columns else 'ANO'

        # Aplicar Filtros se houver
        if unit and unit != 'TODAS':
            df_filtered = df_filtered[df_filtered[col_unit] == unit]
        if month and month != 'TODOS':
            df_filtered = df_filtered[df_filtered[col_month] == month]
        if year and year != 'TODOS':
            df_filtered = df_filtered[df_filtered[col_year].astype(str) == str(year)]

        def get_counts(df, group_col, sort_chronological=False):
            if group_col not in df.columns or df.empty: return []
            counts = df.groupby([group_col, col_hm]).size().unstack(fill_value=0)
            if 'Sim' not in counts.columns: counts['Sim'] = 0
            if 'Não' not in counts.columns: counts['Não'] = 0
            
            result = []
            for label, row in counts.iterrows():
                result.append({
                    "label": str(label),
                    "sim": int(row['Sim']),
                    "nao": int(row['Não']),
                    "total": int(row['Sim'] + row['Não']),
                    "perc": round(row['Sim'] / (row['Sim'] + row['Não']) * 100, 1) if (row['Sim'] + row['Não']) > 0 else 0
                })
            
            if sort_chronological:
                months_ref = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
                def sort_key(r):
                    lbl = str(r['label']).lower()
                    if '/' in lbl:
                        # jan/24 -> year 24, month index
                        parts = lbl.split('/')
                        m_idx = months_ref.index(parts[0]) if parts[0] in months_ref else 99
                        y_val = int(parts[1]) if parts[1].isdigit() else 0
                        return (y_val, m_idx)
                    return (0, months_ref.index(lbl) if lbl in months_ref else 99)
                
                result.sort(key=sort_key)
                
            return result

        # Estatísticas Globais (Filtradas)
        total_sim = int((df_filtered[col_hm].astype(str).str.upper() == 'SIM').sum())
        total_nao = int((df_filtered[col_hm].astype(str).str.upper() == 'NÃO').sum())
        total_total = total_sim + total_nao
        global_perc = round(total_sim / total_total * 100, 1) if total_total > 0 else 0

        # Lógica de Timeline Condicional
        timeline_df = df_filtered.copy()
        is_all_years = str(year).strip().upper() == 'TODOS'
        
        if is_all_years:
            def format_year(y):
                y_str = str(y).replace('.0', '').strip()
                return y_str[-2:] if len(y_str) >= 2 else y_str
            
            timeline_df['TimelineLabel'] = timeline_df[col_month].astype(str) + '/' + timeline_df[col_year].apply(format_year)
            timeline_col = 'TimelineLabel'
        else:
            timeline_col = col_month

        # Lógica de Comparação Histórica para Categorias
        if is_all_years:
            def get_comp_counts(df, cat_col):
                if cat_col not in df.columns or df.empty: return []
                counts = df.groupby([cat_col, col_year, col_hm]).size().unstack(fill_value=0)
                if 'Sim' not in counts.columns: counts['Sim'] = 0
                if 'Não' not in counts.columns: counts['Não'] = 0
                
                result = []
                for (cat_val, year_val), row in counts.iterrows():
                    result.append({
                        "label": f"{str(year_val)} | {str(cat_val)}",
                        "sim": int(row['Sim']),
                        "nao": int(row['Não']),
                        "total": int(row['Sim'] + row['Não']),
                        "perc": round(row['Sim'] / (row['Sim'] + row['Não']) * 100, 1) if (row['Sim'] + row['Não']) > 0 else 0
                    })
                return result

            moments_data = get_comp_counts(df_filtered, col_mom)
            categories_data = get_comp_counts(df_filtered, col_cat)
            units_data = get_comp_counts(df_filtered, col_unit)
        else:
            moments_data = get_counts(df_filtered, col_mom, True)
            categories_data = get_counts(df_filtered, col_cat)
            units_data = get_counts(df_filtered, col_unit)

        return {
            "summary": {
                "global": global_perc,
                "sim": total_sim,
                "nao": total_nao,
                "total": total_total
            },
            "moments": moments_data,
            "categories": categories_data,
            "units": units_data,
            "timeline": get_counts(timeline_df, timeline_col, True),
            "filters": {
                "units": sorted(self.df[col_unit].dropna().unique().tolist()),
                "months": sorted(
                    self.df[col_month].dropna().unique().tolist(),
                    key=lambda m: ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'].index(m.lower()) if m.lower() in ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'] else 99
                ),
                "years": sorted([str(y) for y in self.df[col_year].dropna().unique() if str(y).strip()])
            }
        }

    def get_pivot_data(self):
        if self.df is None: return {}
        
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'
        col_hm = 'HM realizada?' if 'HM realizada?' in self.df.columns else 'HM REALIZADA?'

        pivot = pd.crosstab(
            [self.df[col_cat], self.df[col_mom]], 
            self.df[col_hm], 
            margins=True, 
            margins_name='Total'
        ).fillna(0)

        if 'Sim' in pivot.columns and 'Total' in pivot.columns:
            pivot['% Adesão'] = (pivot['Sim'] / pivot['Total'] * 100).round(1)
        
        return pivot.reset_index().to_dict(orient='records')
