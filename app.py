import streamlit as st
import graphviz

def find_derivations(string_to_parse, grammar):
    """
    Finds derivations and constructs a parse tree using a more robust recursive
    descent parser with memoization and cycle detection to handle recursive grammars.
    """
    memo = {}
    call_stack = set()  # Used to detect and prevent infinite recursion

    def get_parse_tree(string, non_terminal):
        memo_key = (string, non_terminal)
        # 1. Return cached result if already computed
        if memo_key in memo:
            return memo[memo_key]
        # 2. Prevent infinite loops by checking the call stack
        if memo_key in call_stack:
            return None

        call_stack.add(memo_key)

        for production in grammar.get(non_terminal, []):
            # A nested function to backtrack and match a production against a string
            def backtrack(sub_string, production_symbols):
                # Base case: All symbols in the production have been successfully matched
                if not production_symbols:
                    # Success only if the entire sub-string was consumed
                    return [] if not sub_string else None

                current_sym = production_symbols[0]
                remaining_syms = production_symbols[1:]

                # Case 1: Symbol is a terminal (e.g., 'a', 'b', 'c')
                if not current_sym.isupper() and current_sym != 'ε':
                    if sub_string.startswith(current_sym):
                        # If terminal matches, continue with the rest of the string and symbols
                        result = backtrack(sub_string[len(current_sym):], remaining_syms)
                        if result is not None:
                            return [current_sym] + result
                    return None # Mismatch

                # Case 2: Symbol is an epsilon ('ε')
                elif current_sym == 'ε':
                     # Epsilon matches an empty string, so continue with the same string
                    result = backtrack(sub_string, remaining_syms)
                    if result is not None:
                        return ["ε"] + result
                    return None

                # Case 3: Symbol is a non-terminal (e.g., 'S', 'A', 'B')
                else:
                    # Try every possible split of the string
                    for i in range(len(sub_string) + 1):
                        prefix, suffix = sub_string[:i], sub_string[i:]

                        # Recursively find a parse tree for the prefix
                        child_tree = get_parse_tree(prefix, current_sym)

                        if child_tree:
                            # If the prefix works, check if the rest of the string matches
                            remaining_tree = backtrack(suffix, remaining_syms)
                            if remaining_tree is not None:
                                # If both parts match, we found a valid parse
                                return [child_tree] + remaining_tree
                    return None # No split of the string worked for this path

            # Attempt to parse the string with the current production
            # We need to handle the production as a list of symbols if it's not 'ε'
            symbols_in_production = list(production) if production != 'ε' else ['ε']
            tree_children = backtrack(string, symbols_in_production)


            if tree_children is not None:
                # Success! A valid parse was found.
                call_stack.remove(memo_key)
                result = (non_terminal, tree_children)
                memo[memo_key] = result # Cache the successful result
                return result

        # Failure: No production for this non-terminal could parse the string.
        call_stack.remove(memo_key)
        memo[memo_key] = None # Cache the failure
        return None

    # Start the parsing process from the start symbol 'S'
    parse_tree = get_parse_tree(string_to_parse, 'S')

    if not parse_tree:
        return None, None, None

    def get_derivation(tree, current_form, steps, is_lmd):
        steps.append("".join(flatten_form(current_form)))

        non_terminal_to_expand_idx = -1
        search_range = range(len(current_form)) if is_lmd else range(len(current_form) - 1, -1, -1)

        for i in search_range:
            if isinstance(current_form[i], tuple):
                non_terminal_to_expand_idx = i
                break

        if non_terminal_to_expand_idx == -1:
            return

        non_terminal_node = current_form[non_terminal_to_expand_idx]
        _non_terminal, children = non_terminal_node

        new_form = list(current_form)
        new_form[non_terminal_to_expand_idx:non_terminal_to_expand_idx+1] = children

        get_derivation(non_terminal_node, new_form, steps, is_lmd)

    def flatten_form(form_list):
        result = []
        for item in form_list:
            if isinstance(item, str):
                if item != 'ε':
                    result.append(item)
            elif isinstance(item, tuple):
                result.append(item[0])
        return result

    lmd_steps = []
    get_derivation(parse_tree, [parse_tree], lmd_steps, True)

    rmd_steps = []
    get_derivation(parse_tree, [parse_tree], rmd_steps, False)

    return lmd_steps, rmd_steps, parse_tree

def draw_parse_tree_graphviz(tree):
    dot = graphviz.Digraph(comment='Parse Tree', graph_attr={'rankdir': 'TD'})
    dot.attr('node', fontname='Helvetica')
    dot.attr('edge', color='#424242')

    node_counter = 0

    def add_nodes_and_edges(node, parent_id=None):
        nonlocal node_counter
        current_id = str(node_counter)
        node_counter += 1

        if isinstance(node, str):
            label = node
            dot.node(current_id, label, shape='plaintext')
        else:
            non_terminal, children = node
            label = non_terminal
            dot.node(current_id, label, shape='oval', style='filled', fillcolor='#e3f2fd')

            for child in children:
                child_id = add_nodes_and_edges(child, current_id)
                dot.edge(current_id, child_id)

        return current_id

    if tree:
        add_nodes_and_edges(tree)

    return dot

def parse_grammar(grammar_input):
    grammar = {}
    lines = grammar_input.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            if '->' not in line:
                return None, f"Invalid format on line: '{line}'. Missing '->'."

            lhs, rhs = line.split('->', 1)
            non_terminal = lhs.strip()
            productions = [p.strip() for p in rhs.strip().split('|')]

            if non_terminal not in grammar:
                grammar[non_terminal] = []
            grammar[non_terminal].extend(productions)

        except ValueError as e:
            return None, f"Invalid format on line: '{line}'. Error: {e}"

    if 'S' not in grammar:
        return None, "The grammar must contain a starting symbol 'S'."

    return grammar, None

# --- Streamlit UI Code ---

st.set_page_config(layout="wide", page_title="CFG Derivation Explorer")

st.title("CFG Derivation Explorer")
st.markdown("A tool to find derivations and visualize parse trees for any Context-Free Grammar.")

# Re-arranged columns for a logical 1 -> 2 -> 3 flow
col1, col2, col3 = st.columns([1, 1, 1.5])

with col1:
    st.header("1. Grammar Input")
    default_grammar = "S -> SS | a"
    grammar_input = st.text_area("Enter Productions (one per line):", default_grammar, height=200, help="Use 'ε' for epsilon/empty string.")

with col2:
    st.header("2. String & Action")
    target_string = st.text_input("Target String:", "aaa")

    if st.button("Parse String", type="primary", use_container_width=True):
        if 'derivation_state' not in st.session_state:
            st.session_state.derivation_state = {}

        grammar, error = parse_grammar(grammar_input)
        st.session_state.derivation_state['grammar'] = grammar

        if error:
            st.error(error)
            st.session_state.derivation_state['status'] = "Error"
        else:
            with st.spinner('Parsing... This may take a moment for complex grammars.'):
                lmd, rmd, parse_tree = find_derivations(target_string, grammar)

            if parse_tree:
                st.session_state.derivation_state.update({
                    'lmd': lmd,
                    'rmd': rmd,
                    'parse_tree': parse_tree,
                    'status': "Accepted"
                })
                st.success("String Accepted! ✅")
            else:
                st.session_state.derivation_state['status'] = "Rejected"
                st.error("String Rejected! ❌")

with col3:
    st.header("3. Results")
    if 'derivation_state' in st.session_state and 'status' in st.session_state.derivation_state:
        status = st.session_state.derivation_state['status']
        if status == "Accepted":
            lmd_tab, rmd_tab, tree_tab = st.tabs(["Leftmost Derivation", "Rightmost Derivation", "Parse Tree"])

            with lmd_tab:
                st.code(" -> ".join(st.session_state.derivation_state['lmd']), language='text')

            with rmd_tab:
                st.code(" -> ".join(st.session_state.derivation_state['rmd']), language='text')

            with tree_tab:
                st.subheader("Parse Tree Visualization")
                try:
                    dot = draw_parse_tree_graphviz(st.session_state.derivation_state['parse_tree'])
                    st.graphviz_chart(dot)
                except Exception as e:
                    st.error(f"Could not render the parse tree. Error: {e}")

        elif status == "Rejected":
            st.warning("The provided string cannot be derived from the given grammar.")
        elif status == "Error":
             st.error("Please fix the grammar errors before parsing.")
        else:
            st.info("Enter a grammar and string, then click 'Parse String' to see the results.")
    else:
        st.info("Enter a grammar and string, then click 'Parse String' to see the results.")

