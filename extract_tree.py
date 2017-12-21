"""Simple commandline interface for parsing PDF to HTML."""
import argparse
import pdftotree


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="""Script to extract tree structure from PDF files.""")
    parser.add_argument('--model_path', type=str, default=None, help='pretrained model')
    parser.add_argument('--pdf_file', type=str, help='pdf file name for which tree structure needs to be extracted')
    parser.add_argument('--html_path', type=str, help='path where tree structure must be saved', default="./results/")
    parser.add_argument('--favor_figures', type=str, help='whether figures must be favored over other parts such as tables and section headers', default="True")
    parser.add_argument('--visualize', dest="visualize", action="store_true", help='whether to output visualization images for the tree')
    parser.set_defaults(visualize=False)
    args = parser.parse_args()

    # Call the main routine
    pdftotree.parse(args.pdf_file,
                    args.html_path,
                    args.model_path,
                    args.favor_figures,
                    args.visualize)
