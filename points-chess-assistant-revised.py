import chess
import chess.svg
import pygame
import sys
import time
from typing import List, Tuple, Dict, Optional

class PointsChessGame:
    """Core game logic for Points Chess variant"""
    
    # Point values for pieces
    PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0  # King has no point value in standard capture scoring
    }
    
    def __init__(self):
        self.board = chess.Board(fen="8/8/8/8/8/8/8/8 w - - 0 1")  # Empty board
        self.max_moves = 6  # Each player gets 6 moves
        self.moves_played = {'white': 0, 'black': 0}
        self.points_captured = {'white': 0, 'black': 0}
        self.current_player = chess.WHITE  # Will be set based on user selection
        self.game_over = False
        self.winner = None
        self.last_move_was_capture = False
        self.extra_move_granted = False
        
    def set_custom_position(self, fen):
        """Set a custom starting position"""
        try:
            self.board = chess.Board(fen)
            self.reset_game_state()
            return True
        except ValueError:
            print("Invalid FEN string")
            return False
        
    def reset_game_state(self):
        """Reset game state variables"""
        self.moves_played = {'white': 0, 'black': 0}
        self.points_captured = {'white': 0, 'black': 0}
        self.game_over = False
        self.winner = None
        self.last_move_was_capture = False
        self.extra_move_granted = False
    
    def make_move(self, move_uci):
        """Execute a move and update game state"""
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in self.board.legal_moves:
                return False
        except ValueError:
            return False
        
        # Check if move is capturing a piece
        captured_piece = self.board.piece_at(move.to_square)
        self.last_move_was_capture = captured_piece is not None
        
        # Track points for capture
        captured_points = 0
        if captured_piece:
            captured_points = self.PIECE_VALUES[captured_piece.piece_type]
            
            # Check if this is the 6th move and the captured piece is supported
            player = 'white' if self.current_player == chess.WHITE else 'black'
            if self.moves_played[player] == self.max_moves - 1:  # 0-indexed, so 5 is the 6th move
                supported_capture = self._is_square_attacked(
                    move.to_square, 
                    not self.current_player
                )
                if supported_capture:
                    self.extra_move_granted = True
        
        # Execute the move
        self.board.push(move)
        
        # Update points
        player = 'white' if self.current_player == chess.WHITE else 'black'
        self.points_captured[player] += captured_points
        
        # Update moves count
        self.moves_played[player] += 1
        
        # Check for checkmate
        if self.board.is_checkmate():
            self.game_over = True
            self.winner = player
            return True
            
        # Check for game end by move count
        if (self.moves_played['white'] >= self.max_moves and 
            self.moves_played['black'] >= self.max_moves and
            not self.extra_move_granted):
            self.game_over = True
            # Determine winner by points
            if self.points_captured['white'] > self.points_captured['black']:
                self.winner = 'white'
            elif self.points_captured['black'] > self.points_captured['white']:
                self.winner = 'black'
            else:
                self.winner = 'draw'
        
        # Handle extra move logic
        if self.extra_move_granted:
            self.extra_move_granted = False  # Reset the flag
        else:
            # Switch player if no extra move
            self.current_player = not self.current_player
            
        return True
    
    def _is_square_attacked(self, square, by_color):
        """Check if a square is attacked by any piece of the given color"""
        return self.board.is_attacked_by(by_color, square)
    
    def get_legal_moves(self):
        """Get all legal moves in the current position"""
        return [move.uci() for move in self.board.legal_moves]
    
    def evaluate_position(self):
        """Evaluate the current position based on points and checkmate potential"""
        # Base evaluation on material points difference
        if self.game_over:
            if self.winner == 'white':
                return 10000
            elif self.winner == 'black':
                return -10000
            else:
                return 0
                
        # Material evaluation - how many points each side has captured
        material_eval = self.points_captured['white'] - self.points_captured['black']
        
        # Consider checkmate threats
        if self.board.is_check():
            if self.board.turn == chess.WHITE:
                material_eval -= 5  # Black has check against White
            else:
                material_eval += 5  # White has check against Black
        
        # Consider move count - prioritize quick captures as game progresses
        white_moves_left = self.max_moves - self.moves_played['white']
        black_moves_left = self.max_moves - self.moves_played['black']
        
        # Weight captures more heavily when fewer moves remain
        if white_moves_left <= 2 or black_moves_left <= 2:
            material_eval *= 1.5
            
        # Look for immediate captures
        for move in self.board.legal_moves:
            captured_piece = self.board.piece_at(move.to_square)
            if captured_piece:
                capture_value = self.PIECE_VALUES[captured_piece.piece_type]
                if self.board.turn == chess.WHITE:
                    material_eval += capture_value * 0.1  # Small bonus for available captures
                else:
                    material_eval -= capture_value * 0.1
                    
        return material_eval
        
    def skip_turn(self):
        """Skip the current player's turn"""
        player = 'white' if self.current_player == chess.WHITE else 'black'
        self.moves_played[player] += 1
        self.current_player = not self.current_player
        
        # Check for game end
        if (self.moves_played['white'] >= self.max_moves and 
            self.moves_played['black'] >= self.max_moves):
            self.game_over = True
            # Determine winner by points
            if self.points_captured['white'] > self.points_captured['black']:
                self.winner = 'white'
            elif self.points_captured['black'] > self.points_captured['white']:
                self.winner = 'black'
            else:
                self.winner = 'draw'
        
        return True


class ChessEngine:
    """Chess engine for points chess variant"""
    
    def __init__(self, game, max_time=5):
        self.game = game
        self.max_time = max_time  # Maximum time in seconds for move calculation
        self.transposition_table = {}  # For storing evaluated positions
        self.piece_square_tables = self._initialize_piece_square_tables()
        
    def _initialize_piece_square_tables(self):
        """Initialize piece-square tables for position evaluation"""
        # Simple piece-square tables (center control is good for most pieces)
        pst = {}
        
        # Pawns: advance and control center
        pst[chess.PAWN] = [
            0,  0,  0,  0,  0,  0,  0,  0,
            5, 10, 10,-20,-20, 10, 10,  5,
            5, -5,-10,  0,  0,-10, -5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5,  5, 10, 25, 25, 10,  5,  5,
            10, 10, 20, 30, 30, 20, 10, 10,
            50, 50, 50, 50, 50, 50, 50, 50,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        
        # Knights: prefer center, avoid edges
        pst[chess.KNIGHT] = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]
        
        # Bishops: prefer diagonals
        pst[chess.BISHOP] = [
            -20,-10,-10,-10,-10,-10,-10,-20,
            -10,  5,  0,  0,  0,  0,  5,-10,
            -10, 10, 10, 10, 10, 10, 10,-10,
            -10,  0, 10, 10, 10, 10,  0,-10,
            -10,  5,  5, 10, 10,  5,  5,-10,
            -10,  0,  5, 10, 10,  5,  0,-10,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -20,-10,-10,-10,-10,-10,-10,-20
        ]
        
        # Rooks: prefer open files
        pst[chess.ROOK] = [
            0,  0,  0,  5,  5,  0,  0,  0,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            5, 10, 10, 10, 10, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        
        # Queen: combine rook and bishop patterns
        pst[chess.QUEEN] = [
            -20,-10,-10, -5, -5,-10,-10,-20,
            -10,  0,  5,  0,  0,  0,  0,-10,
            -10,  5,  5,  5,  5,  5,  0,-10,
            0,  0,  5,  5,  5,  5,  0, -5,
            -5,  0,  5,  5,  5,  5,  0, -5,
            -10,  0,  5,  5,  5,  5,  0,-10,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -20,-10,-10, -5, -5,-10,-10,-20
        ]
        
        # King: safety and shelter
        pst[chess.KING] = [
            20, 30, 10,  0,  0, 10, 30, 20,
            20, 20,  0,  0,  0,  0, 20, 20,
            -10,-20,-20,-20,-20,-20,-20,-10,
            -20,-30,-30,-40,-40,-30,-30,-20,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30
        ]
        
        return pst
        
    def find_best_move(self, time_limit=None):
        """Find the best move in the current position within time limit"""
        if time_limit is None:
            time_limit = self.max_time
            
        start_time = time.time()
        legal_moves = self.game.get_legal_moves()
        
        if not legal_moves:
            return None
            
        # Start with a basic 1-ply search to get a move quickly
        best_move = self._get_fast_move(legal_moves)
        
        # Iterative deepening - increase depth until time runs out
        for depth in range(1, 10):  # Max depth of 10 plies
            if time.time() - start_time > time_limit * 0.8:  # Use 80% of time limit
                break
                
            try:
                move = self._iterative_deepening_search(depth, time_limit - (time.time() - start_time))
                if move:
                    best_move = move
            except TimeoutError:
                break
                
        return best_move
        
    def _get_fast_move(self, legal_moves):
        """Quick evaluation of moves to get a reasonable move fast"""
        best_score = float('-inf') if self.game.current_player == chess.WHITE else float('inf')
        best_move = legal_moves[0]
        
        for move_uci in legal_moves:
            # Check if move is a capture
            move = chess.Move.from_uci(move_uci)
            captured_piece = self.game.board.piece_at(move.to_square)
            
            # Simple scoring based on material and basic positional values
            score = 0
            
            # Material value of capture
            if captured_piece:
                score += self.game.PIECE_VALUES[captured_piece.piece_type] * 10
                
            # Piece-square table value
            from_sq = move.from_square
            to_sq = move.to_square
            piece = self.game.board.piece_at(from_sq)
            if piece:
                # Subtract value of current position
                score -= self.piece_square_tables[piece.piece_type][from_sq] * 0.1
                # Add value of new position
                score += self.piece_square_tables[piece.piece_type][to_sq] * 0.1
                
            # Check if move gives check
            board_copy = self.game.board.copy()
            board_copy.push(move)
            if board_copy.is_check():
                score += 5
                
            # Update best move
            if self.game.current_player == chess.WHITE and score > best_score:
                best_score = score
                best_move = move_uci
            elif self.game.current_player == chess.BLACK and score < best_score:
                best_score = score
                best_move = move_uci
                
        return best_move
        
    def _iterative_deepening_search(self, depth, time_limit):
        """Perform iterative deepening search with time limit"""
        start_time = time.time()
        
        legal_moves = self.game.get_legal_moves()
        if not legal_moves:
            return None
            
        best_score = float('-inf') if self.game.current_player == chess.WHITE else float('inf')
        best_move = legal_moves[0]
        
        # Order moves: captures first, then checks, then others
        ordered_moves = self._order_moves(legal_moves)
        
        for move_uci in ordered_moves:
            # Check time
            if time.time() - start_time > time_limit * 0.8:
                raise TimeoutError("Search timed out")
                
            # Create a copy of the game to simulate the move
            game_copy = self._clone_game(self.game)
            game_copy.make_move(move_uci)
            
            # Evaluate the move
            score = self._negamax(game_copy, depth - 1, -float('inf'), float('inf'), 
                                -1 if self.game.current_player == chess.WHITE else 1, 
                                start_time, time_limit)
            
            # Invert score for black
            if self.game.current_player == chess.BLACK:
                score = -score
                
            # Update best move
            if self.game.current_player == chess.WHITE and score > best_score:
                best_score = score
                best_move = move_uci
            elif self.game.current_player == chess.BLACK and score < best_score:
                best_score = score
                best_move = move_uci
                
        return best_move
        
    def _order_moves(self, moves):
        """Order moves to improve alpha-beta pruning efficiency"""
        scored_moves = []
        
        for move_uci in moves:
            move = chess.Move.from_uci(move_uci)
            score = 0
            
            # Prioritize captures
            captured_piece = self.game.board.piece_at(move.to_square)
            if captured_piece:
                score += self.game.PIECE_VALUES[captured_piece.piece_type] * 100
                
                # MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
                attacker = self.game.board.piece_at(move.from_square)
                if attacker:
                    score += 10 - self.game.PIECE_VALUES[attacker.piece_type]
                    
            # Prioritize checks
            board_copy = self.game.board.copy()
            board_copy.push(move)
            if board_copy.is_check():
                score += 50
                
            # Use piece-square tables
            piece = self.game.board.piece_at(move.from_square)
            if piece:
                to_sq = move.to_square
                score += self.piece_square_tables[piece.piece_type][to_sq] * 0.1
                
            scored_moves.append((move_uci, score))
            
        # Sort moves by score (descending)
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        
        return [move for move, _ in scored_moves]
        
    def _negamax(self, game, depth, alpha, beta, color, start_time, time_limit):
        """Negamax algorithm with alpha-beta pruning and time limit"""
        # Check time
        if time.time() - start_time > time_limit * 0.8:
            raise TimeoutError("Search timed out")
            
        # Position hash for transposition table
        pos_hash = self._get_position_hash(game)
        
        # Check transposition table
        if pos_hash in self.transposition_table and self.transposition_table[pos_hash]['depth'] >= depth:
            return self.transposition_table[pos_hash]['score']
            
        if depth == 0 or game.game_over:
            score = color * self._evaluate_position(game)
            self.transposition_table[pos_hash] = {'score': score, 'depth': depth}
            return score
            
        max_score = -float('inf')
        
        # Order moves for better pruning
        ordered_moves = self._order_moves(game.get_legal_moves())
        
        for move_uci in ordered_moves:
            game_copy = self._clone_game(game)
            game_copy.make_move(move_uci)
            
            score = -self._negamax(game_copy, depth - 1, -beta, -alpha, -color, start_time, time_limit)
            max_score = max(max_score, score)
            alpha = max(alpha, score)
            
            if alpha >= beta:
                break
                
        # Store in transposition table
        self.transposition_table[pos_hash] = {'score': max_score, 'depth': depth}
        
        return max_score
        
    def _evaluate_position(self, game):
        """Evaluate the position from the perspective of the current player"""
        # Use the game's built-in evaluation
        eval_score = game.evaluate_position()
        
        # Adjust based on current player
        if game.current_player == chess.BLACK:
            eval_score = -eval_score
            
        return eval_score
        
    def _get_position_hash(self, game):
        """Create a unique hash for the current position"""
        return game.board.fen() + str(game.moves_played)
        
    def _clone_game(self, game):
        """Create a deep copy of the game state"""
        new_game = PointsChessGame()
        new_game.board = game.board.copy()
        new_game.moves_played = game.moves_played.copy()
        new_game.points_captured = game.points_captured.copy()
        new_game.current_player = game.current_player
        new_game.game_over = game.game_over
        new_game.winner = game.winner
        new_game.last_move_was_capture = game.last_move_was_capture
        new_game.extra_move_granted = game.extra_move_granted
        return new_game


class ManualPositionSetup:
    """Interface for manual position setup"""
    
    def __init__(self):
        self.selected_piece = None
        self.piece_mapping = {
            'P': chess.PAWN, 'N': chess.KNIGHT, 'B': chess.BISHOP, 
            'R': chess.ROOK, 'Q': chess.QUEEN, 'K': chess.KING,
            'p': chess.PAWN, 'n': chess.KNIGHT, 'b': chess.BISHOP, 
            'r': chess.ROOK, 'q': chess.QUEEN, 'k': chess.KING
        }
        
        # Initialize empty board
        self.board = chess.Board(fen="8/8/8/8/8/8/8/8 w - - 0 1")
        
    def add_piece(self, piece_symbol, square):
        """Add a piece to the board"""
        if piece_symbol in self.piece_mapping:
            color = chess.WHITE if piece_symbol.isupper() else chess.BLACK
            piece_type = self.piece_mapping[piece_symbol]
            self.board.set_piece_at(square, chess.Piece(piece_type, color))
            
    def remove_piece(self, square):
        """Remove a piece from the board"""
        self.board.remove_piece_at(square)
        
    def clear_board(self):
        """Clear the board"""
        self.board = chess.Board(fen="8/8/8/8/8/8/8/8 w - - 0 1")
        
    def get_fen(self):
        """Get the FEN string for the current position"""
        return self.board.fen()
        
    def is_valid_position(self):
        """Check if the position is valid"""
        # Check if both kings are present
        white_king = False
        black_king = False
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.piece_type == chess.KING:
                if piece.color == chess.WHITE:
                    white_king = True
                else:
                    black_king = True
                    
        return white_king and black_king


class ChessUI:
    """User interface for chess assistant"""
    
    def __init__(self):
        self.game = PointsChessGame()
        self.engine = ChessEngine(self.game)
        self.position_setup = ManualPositionSetup()
        self.setup_mode = True
        
        # Initialize pygame
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Points Chess Assistant")
        
        # Load chess piece images
        self.piece_images = self._load_piece_images()
        
        # Define colors
        self.white = (255, 255, 255)
        self.black = (0, 0, 0)
        self.light_square = (240, 217, 181)
        self.dark_square = (181, 136, 99)
        self.highlight = (255, 255, 0, 128)  # Transparent yellow
        self.hint_color = (0, 255, 0, 128)  # Transparent green
        
        # Define board dimensions
        self.board_size = 400
        self.square_size = self.board_size // 8
        self.board_offset_x = 50
        self.board_offset_y = 50
        
        # Setup mode variables
        self.selected_piece_type = None
        self.hint_move = None
        
    def _load_piece_images(self):
        """Load chess piece images"""
        # This is a placeholder - in a real implementation, load actual images
        pieces = {}
        piece_symbols = ['P', 'N', 'B', 'R', 'Q', 'K', 'p', 'n', 'b', 'r', 'q', 'k']
        
        for symbol in piece_symbols:
            # Create a surface for each piece
            piece_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
            
            # Draw a simple representation
            color = self.white if symbol.isupper() else self.black
            pygame.draw.circle(piece_surface, color, 
                             (self.square_size // 2, self.square_size // 2), 
                             self.square_size // 2 - 5)
            
            # Add the piece symbol
            font = pygame.font.SysFont(None, 30)
            text = font.render(symbol, True, self.black if symbol.isupper() else self.white)
            text_rect = text.get_rect(center=(self.square_size // 2, self.square_size // 2))
            piece_surface.blit(text, text_rect)
            
            pieces[symbol] = piece_surface
            
        return pieces
        
    def run(self):
        """Main UI loop"""
        running = True
        selected_square = None
        clock = pygame.time.Clock()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Handle mouse click
                    x, y = event.pos
                    
                    # Check if click is on the chess board
                    if (self.board_offset_x <= x < self.board_offset_x + self.board_size and
                        self.board_offset_y <= y < self.board_offset_y + self.board_size):
                        file = (x - self.board_offset_x) // self.square_size
                        rank = 7 - (y - self.board_offset_y) // self.square_size
                        square = rank * 8 + file
                        
                        if self.setup_mode:
                            # Setup mode: add or remove pieces
                            if self.selected_piece_type:
                                self.position_setup.add_piece(self.selected_piece_type, square)
                            else:
                                # Remove piece if no piece type is selected
                                self.position_setup.remove_piece(square)
                        else:
                            # Game mode: handle piece selection and movement
                            if selected_square is None:
                                # Select piece
                                piece = self.game.board.piece_at(square)
                                if piece and piece.color == self.game.current_player:
                                    selected_square = square
                            else:
                                # Try to move the piece
                                move = chess.Move(selected_square, square)
                                move_uci = move.uci()
                                if move_uci in self.game.get_legal_moves():
                                    self.game.make_move(move_uci)
                                    self.hint_move = None  # Clear hint after move
                                selected_square = None
                    
                    # Check if click is on setup buttons
                    elif self.setup_mode and 500 <= x <= 750:
                        if 50 <= y <= 80:
                            # White pawn
                            self.selected_piece_type = 'P'
                        elif 90 <= y <= 120:
                            # White knight
                            self.selected_piece_type = 'N'
                        elif 130 <= y <= 160:
                            # White bishop
                            self.selected_piece_type = 'B'
                        elif 170 <= y <= 200:
                            # White rook
                            self.selected_piece_type = 'R'
                        elif 210 <= y <= 240:
                            # White queen
                            self.selected_piece_type = 'Q'
                        elif 250 <= y <= 280:
                            # White king
                            self.selected_piece_type = 'K'
                        elif 290 <= y <= 320:
                            # Black pawn
                            self.selected_piece_type = 'p'
                        elif 330 <= y <= 360:
                            # Black knight
                            self.selected_piece_type = 'n'
                        elif 370 <= y <= 400:
                            # Black bishop
                            self.selected_piece_type = 'b'
                        elif 410 <= y <= 440:
                            # Black rook
                            self.selected_piece_type = 'r'
                        elif 450 <= y <= 480:
                            # Black queen
                            self.selected_piece_type = 'q'
                        elif 490 <= y <= 520:
                            # Black king
                            self.selected_piece_type = 'k'
                        elif 530 <= y <= 560:
                            # Clear selection
                            self.selected_piece_type = None
                    
                    # Check if click is on main buttons
                    elif 500 <= x <= 750 and 530 <= y <= 560:
                        if self.setup_mode:
                            # "Start Game" button
                            if self.position_setup.is_valid_position():
                                self.game.set_custom_position(self.position_setup.get_fen())
                                