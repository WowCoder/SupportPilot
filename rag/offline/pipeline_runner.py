"""
CLI runner for the RAG offline ETL pipeline.

Usage:
    python -m rag.offline.pipeline_runner --input doc.pdf --strategy auto
    python -m rag.offline.pipeline_runner --input data/ --pattern "*.txt"
    python -m rag.offline.pipeline_runner --input doc.pdf \\
        --strategy sentence --chunk-size 800 --chunk-overlap 100
    python -m rag.offline.pipeline_runner --input data/ \\
        --compare "sentence,800,100" "sentence,1000,150" "semantic,auto,auto"
"""

import argparse
import logging
import os
import sys
import time

from rag.offline.pipeline import rag_utils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


# ======================================================================
# Argument parser
# ======================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='RAG offline ETL pipeline CLI runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  # Single file\n'
            '  python -m rag.offline.pipeline_runner --input doc.pdf\n\n'
            '  # Batch mode\n'
            '  python -m rag.offline.pipeline_runner --input docs/ --pattern "*.pdf"\n\n'
            '  # Comparison mode\n'
            '  python -m rag.offline.pipeline_runner --input doc.pdf --compare '
            '"sentence,800,100" "sentence,1000,150"\n'
        ),
    )

    input_group = parser.add_argument_group('Input')
    input_group.add_argument(
        '--input', '-i',
        required=True,
        help='Path to a single file or a directory (batch mode)',
    )
    input_group.add_argument(
        '--pattern', '-p',
        default='*',
        help='Glob pattern for batch mode (default: *)',
    )

    chunk_group = parser.add_argument_group('Chunking')
    chunk_group.add_argument(
        '--strategy', '-s',
        default='auto',
        choices=['auto', 'sentence', 'semantic', 'recursive', 'small_to_big'],
        help='Chunking strategy (default: auto)',
    )
    chunk_group.add_argument(
        '--chunk-size', '-c',
        type=int,
        default=1000,
        help='Target chunk size in characters (default: 1000)',
    )
    chunk_group.add_argument(
        '--chunk-overlap', '-o',
        type=int,
        default=150,
        help='Chunk overlap in characters (default: 150)',
    )

    stb_group = parser.add_argument_group('Small-to-Big')
    stb_group.add_argument(
        '--use-small-to-big', '-stb',
        action='store_true',
        help='Enable small-to-big chunking',
    )
    stb_group.add_argument(
        '--parent-size',
        type=int,
        default=2000,
        help='Parent chunk size for small-to-big (default: 2000)',
    )
    stb_group.add_argument(
        '--child-size',
        type=int,
        default=500,
        help='Child chunk size for small-to-big (default: 500)',
    )

    compare_group = parser.add_argument_group('Comparison')
    compare_group.add_argument(
        '--compare', '-C',
        nargs='*',
        metavar='STRATEGY,SIZE,OVERLAP',
        help=(
            'Compare multiple strategies. Each spec is "strategy,size,overlap", '
            'e.g. --compare "sentence,800,100" "sentence,1000,150" '
            '"semantic,auto,auto"'
        ),
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging',
    )

    return parser


# ======================================================================
# Helpers
# ======================================================================

def _parse_compare_spec(spec: str):
    """Parse a comparison spec string into (strategy, chunk_size, chunk_overlap).

    Accepts formats:
        "sentence,800,100"
        "sentence,auto,auto"
        "semantic"
    """
    parts = spec.split(',')
    strategy = parts[0]
    chunk_size = int(parts[1]) if len(parts) > 1 and parts[1] not in ('auto', '') else 1000
    chunk_overlap = int(parts[2]) if len(parts) > 2 and parts[2] not in ('auto', '') else 150
    return strategy, chunk_size, chunk_overlap


# ======================================================================
# Mode runners
# ======================================================================

def run_single(pipeline, args) -> dict:
    """Process a single file and print the result."""
    logger.info('Processing single file: %s', args.input)
    logger.info(
        '  Strategy: %s, chunk_size=%d, overlap=%d, small_to_big=%s',
        args.strategy, args.chunk_size, args.chunk_overlap,
        args.use_small_to_big,
    )

    start = time.time()
    result = pipeline.run(
        args.input,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        use_small_to_big=args.use_small_to_big,
        parent_size=args.parent_size,
        child_size=args.child_size,
    )
    elapsed = time.time() - start
    result['elapsed'] = elapsed

    print_result(result)
    return result


def run_batch(pipeline, args) -> list:
    """Process all matching files in a directory with a progress indicator."""
    import glob

    files = sorted(glob.glob(os.path.join(args.input, args.pattern)))
    if not files:
        logger.warning('No files matched pattern "%s" in %s', args.pattern, args.input)
        return []

    # Filter to files only (no directories)
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        logger.warning('No files (only directories) matched pattern "%s" in %s', args.pattern, args.input)
        return []

    total = len(files)
    logger.info('Batch processing %d file(s) from %s (pattern: %s)', total, args.input, args.pattern)
    logger.info('  Strategy: %s, chunk_size=%d, overlap=%d', args.strategy, args.chunk_size, args.chunk_overlap)

    results = []
    failures = 0
    total_chunks = 0
    batch_start = time.time()

    for idx, file_path in enumerate(files, 1):
        progress = f'[{idx}/{total}]'
        name = os.path.basename(file_path)

        sys.stdout.write(f'\r  {progress} Processing: {name:<50}')
        sys.stdout.flush()

        try:
            start = time.time()
            result = pipeline.run(
                file_path,
                strategy=args.strategy,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                use_small_to_big=args.use_small_to_big,
                parent_size=args.parent_size,
                child_size=args.child_size,
            )
            elapsed = time.time() - start
            result['elapsed'] = elapsed
            added = result.get('chunks_added', 0)
            total_chunks += added
            results.append((file_path, result))

            status = f'OK (+{added} chunks, {elapsed:.1f}s)'
        except Exception as e:
            elapsed = time.time() - start
            failures += 1
            results.append((file_path, {'success': False, 'error': str(e), 'elapsed': elapsed}))
            status = f'FAIL ({e})'

        sys.stdout.write(f'\r  {progress} {name:<50} {status:<35}')
        sys.stdout.write('\n')
        sys.stdout.flush()

    batch_elapsed = time.time() - batch_start
    print_summary_batch(results, total, failures, total_chunks, batch_elapsed)
    return results


def run_comparison(pipeline, args) -> list:
    """Compare multiple strategies on the same input file."""
    specs = args.compare
    if not specs:
        logger.error('No comparison specs provided')
        return []

    file_path = args.input
    if not os.path.isfile(file_path):
        logger.error('Comparison mode requires a single file, got: %s', file_path)
        return []

    file_size = os.path.getsize(file_path)
    logger.info('Comparison mode: %d spec(s) on %s (%.1f KB)', len(specs), file_path, file_size / 1024)
    logger.info('')

    comparison_results = []

    for spec in specs:
        strategy, chunk_size, chunk_overlap = _parse_compare_spec(spec)

        logger.info('  Running: %s (size=%d, overlap=%d)...', strategy, chunk_size, chunk_overlap)

        start = time.time()
        try:
            result = pipeline.run(
                file_path,
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_small_to_big=args.use_small_to_big,
                parent_size=args.parent_size,
                child_size=args.child_size,
            )
            elapsed = time.time() - start
            result['elapsed'] = elapsed
            result['config_strategy'] = strategy
            result['config_chunk_size'] = chunk_size
            result['config_chunk_overlap'] = chunk_overlap

            total_chunks = result.get('chunks_total', 0)
            if total_chunks > 0:
                total_chars = result.get('total_chars', 0)
                avg_size = total_chars // total_chunks
            else:
                avg_size = 0

            comparison_results.append({
                'strategy': strategy,
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap,
                'total_chunks': total_chunks,
                'avg_chunk_size': avg_size,
                'elapsed': elapsed,
                'success': True,
            })

            logger.info('    -> %d chunks, avg %d chars, %.2f s', total_chunks, avg_size, elapsed)

        except Exception as e:
            elapsed = time.time() - start
            comparison_results.append({
                'strategy': strategy,
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap,
                'total_chunks': 0,
                'avg_chunk_size': 0,
                'elapsed': elapsed,
                'success': False,
                'error': str(e),
            })
            logger.info('    -> FAIL: %s', e)

    print_comparison(comparison_results)
    return comparison_results


# ======================================================================
# Output formatting
# ======================================================================

def print_result(result: dict):
    """Print a single-file processing result."""
    success = result.get('success', True)
    if not success:
        print('  Status: FAILED')
        print(f"  Error: {result.get('error', 'Unknown error')}")
        return

    print('  Status: OK')
    print(f"  Strategy: {result.get('strategy')}")
    print(f"  Chunks added: {result.get('chunks_added', 0)} / {result.get('chunks_total', 0)}")
    print(f"  Small-to-big: {result.get('use_small_to_big', False)}")
    print(f"  Time: {result.get('elapsed', 0):.2f}s")


def print_summary_batch(results: list, total: int, failures: int,
                        total_chunks: int, elapsed: float):
    """Print batch processing summary."""
    print('')
    print('=' * 60)
    print('  Batch Summary')
    print(f'  {"Files processed:":<20} {total}')
    print(f'  {"Failures:":<20} {failures}')
    print(f'  {"Total chunks added:":<20} {total_chunks}')
    print(f'  {"Total time:":<20} {elapsed:.2f}s')
    print(f'  {"Avg time/file:":<20} {elapsed / max(total, 1):.2f}s')
    print('=' * 60)


def print_comparison(comparison_results: list):
    """Print a side-by-side strategy comparison table."""
    if not comparison_results:
        return

    print('')
    print('=' * 80)
    print('  Strategy Comparison')
    print('=' * 80)

    # Header
    header = (f'  {"Strategy":<15} {"Chunk Sz":<10} {"Overlap":<9} '
              f'{"Chunks":<8} {"Avg Sz":<8} {"Time":<10} Status')
    print(header)
    print('  ' + '-' * 72)

    for r in comparison_results:
        status = 'OK' if r['success'] else 'FAIL'
        strategy = r['strategy']
        # Truncate strategy name if too long
        if len(strategy) > 14:
            strategy = strategy[:12] + '..'
        print(
            f'  {strategy:<15} '
            f'{r["chunk_size"]:<12} '
            f'{r["chunk_overlap"]:<10} '
            f'{r["total_chunks"]:<10} '
            f'{r["avg_chunk_size"]:<10} '
            f'{r["elapsed"]:<10.2f} '
            f'{status}'
        )

    print('=' * 80)


# ======================================================================
# Main entry point
# ======================================================================

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input
    if not os.path.exists(args.input):
        parser.error(f'Input path does not exist: {args.input}')

    pipeline = rag_utils._pipeline

    if args.compare:
        run_comparison(pipeline, args)
    elif os.path.isdir(args.input):
        run_batch(pipeline, args)
    else:
        run_single(pipeline, args)


if __name__ == '__main__':
    main()
