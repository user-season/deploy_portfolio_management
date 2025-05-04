from datetime import datetime
from vnstock import Vnstock
from .models import Asset
import pandas as pd




# Khởi tạo Vnstock
vnstock_instance = Vnstock()
stock = vnstock_instance.stock(symbol='VN30', source='VCI')

def get_list_stock_market():
    """Lấy danh sách mã cổ phiếu niêm yết"""
    try:
        symbols_df = stock.listing.all_symbols()
        if symbols_df.empty:
            print("WARNING: No stock symbols retrieved from vnstock")
            return []
        return symbols_df['ticker'].values.tolist()
    except Exception as e:
        print(f"Error in get_list_stock_market: {str(e)}")
        return []

def get_price_board():
    """Lấy bảng giá thị trường"""
    try:
        # Get a limited set of symbols first to ensure we get some data
        symbols = get_list_stock_market()
        if not symbols:
            print("WARNING: No symbols to fetch price board")
            return pd.DataFrame()
            
        # For testing, limit to first 50 symbols to avoid timeouts or data size issues
        test_symbols = symbols[:50]
        print(f"Fetching price board for {len(test_symbols)} symbols...")
        
        try:
            # Try with VCI source first
            price_board = stock.trading.price_board(symbols_list=test_symbols)
        except Exception as e:
            print(f"Error with VCI source: {str(e)}, trying SSI source...")
            # Fall back to SSI source if VCI fails
            ssi_stock = vnstock_instance.stock(symbol='VN30', source='SSI')
            price_board = ssi_stock.trading.price_board(symbols_list=test_symbols)
        
        # Check if we got data
        if price_board.empty:
            print("WARNING: Empty price board returned from vnstock")
            # Create a minimal dataframe with required columns for debugging
            return pd.DataFrame({
                ('listing', 'symbol'): ['AAA', 'VNM', 'FPT'],
                ('listing', 'ceiling'): [25000, 60000, 90000],
                ('listing', 'floor'): [20000, 50000, 80000],
                ('listing', 'ref_price'): [22000, 55000, 85000],
                ('match', 'match_price'): [22500, 56000, 86000],
                ('match', 'match_vol'): [10000, 5000, 3000]
            })
            
        print(f"Price board fetched: {len(price_board)} rows")
        print(f"Price board columns: {price_board.columns}")
        
        if isinstance(price_board.columns, pd.MultiIndex):
            price_board.columns = ['_'.join(map(str, col)).strip() for col in price_board.columns.values]
            print(f"Flattened columns: {price_board.columns}")
        
        # Check that we have the necessary columns
        required_cols = ['listing_symbol', 'listing_ceiling', 'listing_floor', 'listing_ref_price', 'match_match_price', 'match_match_vol']
        alt_cols = ['symbol', 'ceiling', 'floor', 'ref_price', 'match_price', 'match_vol']
        
        columns_present = all(col in price_board.columns for col in required_cols) or all(col in price_board.columns for col in alt_cols)
        
        if not columns_present:
            print(f"WARNING: Missing required columns in price board. Available columns: {price_board.columns}")
            # Try to map columns differently
            if isinstance(price_board.columns, pd.MultiIndex):
                # Try another method to flatten
                price_board.columns = [f"{col[0]}_{col[1]}" for col in price_board.columns]
            else:
                # Try to rename columns if they exist with different names
                column_map = {}
                for req, alt in zip(required_cols, alt_cols):
                    if alt in price_board.columns:
                        column_map[alt] = req
                
                if column_map:
                    price_board = price_board.rename(columns=column_map)
        
        # Final check
        print(f"Final columns: {price_board.columns}")
        return price_board
    except Exception as e:
        print(f"Error in get_price_board: {str(e)}")
        # Return a fallback dataframe with sample data for debugging
        return pd.DataFrame({
            'listing_symbol': ['AAA', 'VNM', 'FPT'],
            'listing_ceiling': [25000, 60000, 90000],
            'listing_floor': [20000, 50000, 80000],
            'listing_ref_price': [22000, 55000, 85000],
            'match_match_price': [22500, 56000, 86000],
            'match_match_vol': [10000, 5000, 3000]
        })

def sync_vnstock_to_assets():
    """Đồng bộ dữ liệu từ vnstock vào model Asset"""
    try:
        symbols_df = stock.listing.all_symbols()
        if symbols_df.empty:
            print("ERROR: No stock symbols retrieved from vnstock")
            return {'created': 0, 'updated': 0, 'errors': 0, 'total': 0}

        print(f"Found {len(symbols_df)} stocks in VNStock")
        symbols = symbols_df['ticker'].tolist()  # Lấy tất cả mã, không giới hạn 20

        # Lấy bảng giá
        price_board = stock.trading.price_board(symbols_list=symbols)
        if isinstance(price_board.columns, pd.MultiIndex):
            price_board.columns = ['_'.join(map(str, col)).strip() for col in price_board.columns.values]

        created_count = 0
        updated_count = 0
        error_count = 0

        for symbol in symbols:
            try:
                symbol_info = symbols_df[symbols_df['ticker'] == symbol].iloc[0]
                price_row = price_board[price_board['listing_symbol'] == symbol]
                current_price = price_row['match_match_price'].values[0] if not price_row.empty and 'match_match_price' in price_board.columns else 10000

                asset, created = Asset.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        'name': symbol_info['organ_name'],
                        'type': 'stock',
                        'sector': symbol_info.get('industry_name', 'Unknown'),
                        'current_price': current_price,
                        'description': f"Imported from VNStock on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                )
                if created:
                    created_count += 1
                    print(f"Created asset: {symbol} - {symbol_info['organ_name']}")
                else:
                    updated_count += 1
                    print(f"Updated asset: {symbol} - {symbol_info['organ_name']}")
            except Exception as e:
                error_count += 1
                print(f"Error processing {symbol}: {str(e)}")

        return {
            'created': created_count,
            'updated': updated_count,
            'errors': error_count,
            'total': created_count + updated_count
        }
    except Exception as e:
        print(f"Error syncing VNStock data: {str(e)}")
        return {'created': 0, 'updated': 0, 'errors': 1, 'total': 0}