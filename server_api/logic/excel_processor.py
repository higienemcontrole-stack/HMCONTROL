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
                # A Tabulação Geral inicia vazia e é preenchida pelo Supabase/Extern
                self.df = pd.DataFrame(columns=[
                    'Mês (automático)', 'Ano (automático)', 'Observador', 'Unidade', 
                    'Profissional Auditado', 'Momento Auditado', 'Produto utilizado', 
                    'Login', 'Horário'
                ])
                logger.log_system("ExcelProcessor: Estrutura inicial pronta (Modo Volume).")
            except Exception as e:
                logger.log_error("EXCEL_LOAD_VALIDATIONS", str(e))

    def update_from_external_data(self, data_list):
        # Resetar o DF atual
        self.df = pd.DataFrame(columns=[
            'Mês (automático)', 'Ano (automático)', 'Observador', 'Unidade', 
            'Profissional Auditado', 'Momento Auditado', 'Produto utilizado', 
            'Login', 'Horário'
        ])
        
        if not data_list:
            logger.log_system("ExcelProcessor: Nenhum dado recebido. DF permanece vazio.", level=30)
            return

        new_df = pd.DataFrame(data_list)
        if not new_df.empty:
            self.df = new_df
            logger.log_system(f"ExcelProcessor: 100% SUPABASE SYNC - {len(self.df)} monitoramentos.")

    def get_dropdown_lists(self):
        if self.validations_df is None: return {}
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
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        
        # Agora o global é apenas o total de monitoramentos
        moments_stats = self.df[col_mom].value_counts().to_dict() if col_mom in self.df.columns else {}
        category_stats = self.df[col_cat].value_counts().to_dict() if col_cat in self.df.columns else {}

        return {
            "global": 100, # Mock 100% se necessário ou remover do front
            "total_audits": total,
            "moments": {str(k): int(v) for k, v in moments_stats.items()},
            "categories": {str(k): int(v) for k, v in category_stats.items()}
        }

    def get_raw_tabulation(self):
        if self.df is None: return []
        return self.df.head(100).fillna('').to_dict(orient='records')

    def get_dashboard_data(self, unit=None, month=None, year=None):
        if self.df is None: return {}
        
        df_filtered = self.df.copy()
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        col_unit = 'Unidade' if 'Unidade' in self.df.columns else 'UNIDADE'
        col_month = 'Mês (automático)' if 'Mês (automático)' in self.df.columns else 'MÊS'
        col_year = 'Ano (automático)' if 'Ano (automático)' in self.df.columns else 'ANO'

        # Aplicar Filtros
        if unit and unit != 'TODAS':
            df_filtered = df_filtered[df_filtered[col_unit] == unit]
        if month and month != 'TODOS':
            df_filtered = df_filtered[df_filtered[col_month] == month]
        if year and year != 'TODOS':
            df_filtered = df_filtered[df_filtered[col_year].astype(str) == str(year)]

        def get_volume_counts(df, group_col, sort_chronological=False):
            if group_col not in df.columns or df.empty: return []
            counts = df[group_col].value_counts().sort_index()
            
            result = []
            for label, count in counts.items():
                result.append({
                    "label": str(label),
                    "total": int(count),
                    "perc": 100 # Sem campo sim/não, mostramos apenas o volume
                })
            
            if sort_chronological:
                months_ref = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
                def sort_key(r):
                    lbl = str(r['label']).lower()
                    if '/' in lbl:
                        parts = lbl.split('/')
                        m_str = parts[0]
                        m_idx = months_ref.index(m_str) if m_str in months_ref else (int(m_str)-1 if m_str.isdigit() else 99)
                        y_val = int(parts[1]) if parts[1].isdigit() else 0
                        return (y_val, m_idx)
                    return (0, months_ref.index(lbl) if lbl in months_ref else (int(lbl)-1 if lbl.isdigit() else 99))
                result.sort(key=sort_key)
            return result

        # Estatísticas Globais
        total_total = len(df_filtered)

        # Lógica de Timeline
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

        return {
            "summary": {
                "global": 100,
                "total": total_total
            },
            "moments": get_volume_counts(df_filtered, col_mom, True),
            "categories": get_volume_counts(df_filtered, col_cat),
            "units": get_volume_counts(df_filtered, col_unit),
            "timeline": get_volume_counts(timeline_df, timeline_col, True),
            "filters": {
                "units": sorted(self.df[col_unit].dropna().unique().tolist()) if not self.df.empty else [],
                "months": sorted(
                    self.df[col_month].dropna().unique().tolist(),
                    key=lambda m: ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'].index(str(m).lower()) if str(m).lower() in ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'] else (int(str(m))-1 if str(m).isdigit() else 99)
                ) if not self.df.empty else [],
                "years": sorted([str(y) for y in self.df[col_year].dropna().unique() if str(y).strip()]) if not self.df.empty else []
            }
        }

    def get_pivot_data(self):
        if self.df is None or self.df.empty: return []
        
        col_cat = 'Profissional Auditado' if 'Profissional Auditado' in self.df.columns else 'CATEGORIA'
        col_mom = 'Momento Auditado' if 'Momento Auditado' in self.df.columns else 'MOMENTO'

        pivot = pd.crosstab(
            self.df[col_cat], 
            self.df[col_mom], 
            margins=True, 
            margins_name='Total'
        ).fillna(0)
        
        return pivot.reset_index().to_dict(orient='records')
