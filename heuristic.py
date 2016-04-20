import logging
import time

# logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("log")
# logger.propagate = False

# global variables
vertices = []
edges = []
vertex_sizes = {}
vertex_colors = []
vertex_bins = []
edge_matchings = []
areas = []
border_elements = []
path_1 = []
path_2 = []
max_bin_size = 0
num_bins = 0
num_colors = 0
bin_assignments = []
bins_by_color = []
input_correct = False
starting_vertices = []
order = []
ordering_valid = False
queue = []
current_color = 0
num_conflicts = 0
index = 0
interpretation = []
INT_TRUE = 1
INT_FALSE = -1
INT_UNKNOWN = 0


fallback_start = -1


class Vertex:
    """A vertex in the problem input graph"""
    def __init__(self, name, var):
        self.name = name
        self.var = var
        self.in_path = 0
        self.ordering_value = 0
        self.num_predecessors = 0
        self.num_successors = 0
        self.neighbors = []
        self.size = 0
        self.all_colors = []
        self.all_bins = []
        self.considered = False


class Edge:
    """A edge that connects two vertices"""
    def __init__(self, v_from, v_to, var):
        self.v_from = v_from
        self.v_to = v_to
        self.var = var


class VertexColor:
    """A vertex color"""
    def __init__(self, vertex, color, var):
        self.vertex = vertex
        self.color = color
        self.var = var


class VertexBin:
    def __init__(self, vertex, v_bin, var):
        self.vertex = vertex
        self.v_bin = v_bin
        self.var = var


class EdgeMatching:
    def __init__(self, area, border_element, var):
        self.area = area
        self.border_element = border_element
        self.var = var
        self.related_area = None


class Area:
    def __init__(self, area, var):
        self.area = area
        self.var = var
        self.selected = False
        self.total = 0
        self.counter = 0


class BorderElement:
    def __init__(self, element, var):
        self.element = element
        self.var = var
        self.used_in = []


class BinAssignment:
    def __init__(self, vertex, color, v_bin, var):
        self.vertex = vertex
        self.vertex_size = 0
        self.color = color
        self.v_bin = v_bin
        self.var = var


class Bin:
    def __init__(self, name):
        self.name = name
        self.all_vertices = []


def init_data():
    """
    Init the data structures.
    :return: True if everything is okay, False if the instance is invalid or unsolvable
    """
    global starting_vertices

    # edges ------------------------------------------------------------------------------------------------------------
    for e in edges:
        num_found = 0
        v_f = None
        v_t = None
        for v in vertices:
            if e.v_from == v.name:
                v_f = v
                num_found += 1
            if v.name == e.v_to:
                v_t = v
                num_found += 1
            if num_found >= 2:
                break

        if num_found != 2:
            return False

        v_f.neighbors.append(v_t)
        v_t.neighbors.append(v_f)
        v_f.num_successors += 1
        v_t.num_predecessors += 1

    # vertex sizes -----------------------------------------------------------------------------------------------------
    for v in vertices:
        if v.name not in vertex_sizes:
            return False
        v.size = vertex_sizes[v.name]

    for ass in bin_assignments:
        if ass.vertex not in vertex_sizes:
            return False
        ass.vertex_size = vertex_sizes[ass.vertex]

    # vertex colors ----------------------------------------------------------------------------------------------------
    for vc in vertex_colors:
        found = False
        for v in vertices:
            if v.name == vc.vertex:
                found = True
                v.all_colors.append(vc)
                break

        if not found:
            return False

    # vertex bins ------------------------------------------------------------------------------------------------------
    for vb in vertex_bins:
        found = False
        for v in vertices:
            if v.name == vb.vertex:
                found = True
                v.all_bins.append(vb)
                break

        if not found:
            return False

    # init bins --------------------------------------------------------------------------------------------------------
    for col in range(0, num_colors):
        bins_by_color.append([Bin(str(i + 1)) for i in range(0, num_bins)])

    for bin_assignment in bin_assignments:
        (bins_by_color[bin_assignment.color - 1])[bin_assignment.v_bin - 1].all_vertices.append(bin_assignment)

    # sort bins and colors ---------------------------------------------------------------------------------------------
    for vertex in vertices:
        vertex.all_bins = sorted(vertex.all_bins, key=lambda b: b.v_bin)
        vertex.all_colors = sorted(vertex.all_colors, key=lambda c: c.color)

    # get matching related edges ---------------------------------------------------------------------------------------
    for border_element in border_elements:
        for edge_matching in edge_matchings:
            if border_element.element == edge_matching.border_element:
                border_element.used_in.append(edge_matching)

    for area in areas:
        for edge_matching in edge_matchings:
            if area.area == edge_matching.area:
                area.total += 1
                edge_matching.related_area = area

    # initialize vertex value for ordering -----------------------------------------------------------------------------
    for v_p in path_1:
        for v in vertices:
            if v_p == v.name:
                v.in_path = 1
                v.ordering_value += 1
                break

    for v_p in path_2:
        for v in vertices:
            if v_p == v.name:
                v.in_path = 2
                v.ordering_value += 1
                break

    for v in vertices:
        if (v.num_predecessors == 0) or (v.num_successors == 0):
            v.ordering_value += 2

        if v.ordering_value > 0:
            starting_vertices.append(v)

    starting_vertices = sorted(starting_vertices, key=lambda u: u.ordering_value, reverse=True)
    logger.debug("sorted starting_vertices:")
    for u in starting_vertices:
        logger.debug("  %s, ordering_value = %d", u.name, u.ordering_value)

    global order
    order = [v for v in vertices]

    reset_heuristic()

    global ordering_valid
    ordering_valid = create_order()
    return True


def fallback():
    """
    Optional. This method should be added if the heuristic wants to use the fallback heuristic at some point
    :return: None
    """


def onVariableUndefined(var):
    """
    Optional. When a variable is set as  undefined (by an unroll).
    :param var: the undefined variable
    :return: None
    """
    global interpretation
    global INT_UNKNOWN
    interpretation[var] = INT_UNKNOWN


def onLiteralsTrue(*lits):
    """
    Optional. When a set of literals is dervied as true either by propagation and by choice
    :param lits: the true literals
    :return: None
    """
    global interpretation
    global INT_TRUE
    global INT_FALSE
    for l in lits:
        interpretation[abs(l)] = INT_TRUE if l >= 0 else INT_FALSE


def get_fallback():
    global fallback_start

    if -1 == fallback_start:
        logger.info("starting fallback")
        reset_heuristic()
        fallback_start = time.time()

    return [1000, 2, 0]


def check_fallback():
    global fallback_start

    fallback_elapsed = (time.time() - fallback_start)

    if 0 <= fallback_elapsed <= 10:
        logger.info("  in fallback (t = %.2f)", fallback_elapsed)
        return True

    fallback_start = -1
    return False


def choiceVars():
    """
    Required. This method is invoked when a choice is needed. It can return a choice, a list of choices and special
    values for performing special actions.
    Special values:
     - [1, 0] force the solver to perform a restart
     - [n, 2, 0] use the fallback heuristic for n steps (n<=0 use always fallback heuristic) -> require the presence of the method fallback() in the script
     - [v, 3, 0] unroll the truth value of the variable v
     - [4, 0] force the solver to stop the computation returning incoherent
    :return: A list of choices. Be careful, the first choice is the last element in the list.
    """

    global index
    global interpretation
    global INT_TRUE
    global INT_FALSE
    global INT_UNKNOWN
    global current_color

    chosen_variable = 0
    bin_chosen = False
    bin_search = False

    logger.debug("start choice_vars()")

    if check_fallback():
        return get_fallback()

    while (chosen_variable == 0) \
            or (interpretation[chosen_variable] != INT_UNKNOWN):

        if not ordering_valid:
            return get_fallback()

        chosen_variable = 0
        current_vertex = 0
        current_vertex_color = 0
        current_vertex_bin = 0

        if not (index < len(order)):
            logger.debug("  index out of range, continue (index = %d, len(order) = %d)", index, len(order))
            continue

        # fill the queue if empty
        if not queue:
            logger.debug("  queue is empty (index = %d)", index)
            if index > 0:
                current_color += 1
                logger.debug("    increase color value to %d", current_color)

                if current_color >= num_colors:
                    logger.debug("    exceeded number of colors, falling back")
                    return get_fallback()

            logger.debug("    searching in order (starting index = %d)", index)
            while current_vertex == 0 and index < len(order):
                logger.debug("      %s considered = %s", order[index].name, order[index].considered)
                if not order[index].considered:
                    current_vertex = order[index]

                index += 1

            if current_vertex == 0:
                return get_fallback()  # fallback for 1000 steps

            queue.append(current_vertex)

        # get the first vertex
        current_vertex = queue[0]
        logger.debug("  current_vertex = %s", current_vertex.name)

        for c in current_vertex.all_colors:
            if interpretation[c.var] == INT_TRUE:
                current_vertex_color = c.color
                logger.debug("  current_vertex_color = %d", c.color)
                break

        if current_vertex_color == 0:
            chosen_variable = current_vertex.all_colors[current_color].var
            logger.debug("  current_vertex_color = %d, setting chosen variable to %d", current_vertex_color, chosen_variable)
        elif current_vertex_color - 1 == current_color:
            current_vertex_bin = 0
            for b in current_vertex.all_bins:
                if interpretation[b.var] == INT_TRUE:
                    current_vertex_bin = b.v_bin
                    logger.debug("  current_vertex_bin = %s", b.v_bin)
                    break

        # find a bin for the vertex if no bin is assigned to it yet
        if chosen_variable == 0 and (current_vertex_color - 1) == current_color and current_vertex_bin == 0:
            bin_search = True

            for i in range(0, num_bins):
                used = 0
                for ba in bins_by_color[current_color][i].all_vertices:
                    if interpretation[ba.var] == INT_TRUE:
                        used += ba.vertex_size

                if used + current_vertex.size <= max_bin_size:
                    logger.debug("  used + current_vertex.size = %d, max_bin_size = %d", (used + current_vertex.size), max_bin_size)
                    chosen_variable = current_vertex.all_bins[i].var
                    bin_chosen = True
                    break

        if chosen_variable == 0:
            logger.debug("  chosen_variable = %d", chosen_variable)
            if current_vertex_color - 1 != current_color:
                logger.debug("vertex %s is not colored in the current color - ignore it", current_vertex.name)
                queue.pop(0)
            elif bin_search:
                logger.debug("no bin found for vertex %s - ignore it", current_vertex.name)
                queue.pop(0)
                current_vertex.considered = True
            elif current_vertex_bin != 0:
                logger.debug("vertex already placed in bin %d", current_vertex_bin)
                queue.pop(0)
                logger.debug("removed vertex from queue. queue size = %d. adding neighbors", len(queue))
                queue_add_neighbors(current_vertex)
                current_vertex.considered = True
        elif interpretation[chosen_variable] == INT_TRUE:
            logger.debug("chosen variable already set to true - continue")
            if bin_chosen:
                queue.pop(0)
                current_vertex.considered = True
        elif interpretation[chosen_variable] == INT_FALSE:
            logger.debug("chosen variable already set to false - continue")
            queue.pop(0)
        elif interpretation[chosen_variable] == INT_UNKNOWN:
            logger.debug("chosen variable is undefined - return it")
        elif bin_chosen:
            queue.pop(0)
            queue_add_neighbors(current_vertex)
            current_vertex.considered = True

    logger.info("choosing variable %d", chosen_variable)
    return [chosen_variable]


def queue_add_neighbors(vertex):
    global queue
    for neighbor in vertex.neighbors:
        if not neighbor.considered \
                and (vertex.in_path == 0 or neighbor.in_path == 0 or vertex.in_path == neighbor.in_path):
            queue.append(neighbor)

    if vertex.in_path > 0:
        queue = sorted(queue, key=lambda vert: vert.in_path, reverse=True)
    else:
        queue = sorted(queue, key=lambda vert: vert.in_path)

    logger.debug("queue_add_neighbors: vertex = %s, in_path = %d. sorted queue", vertex.name, vertex.in_path)
    for v in queue:
        logger.debug("     %s, in_path = %d", v.name, v.in_path)


def ignorePolarity():
    pass


def addedVarName(var, name):
    """
    Optional. This method is invoked while reading the name associated to a variable.
    :param var: the id of the variable
    :param name: the name associated to var
    """

    if name.startswith("vertex("):
        global vertices
        vertices.append(Vertex(name[7:-1], var))
    elif name.startswith("edge("):
        edge = [v for v in name[5:-1].split(",")]
        assert len(edge) == 2
        global edges
        edges.append(Edge(edge[0], edge[1], var))
    elif name.startswith("size("):
        term = [v for v in name[5:-1].split(",")]
        assert len(term) == 2
        global vertex_sizes
        # term[0] = name of the vertex, term[1] = size
        vertex_sizes[term[0]] = int(term[1])
    elif name.startswith("vertex_color("):
        term = [v for v in name[13:-1].split(",")]
        assert len(term) == 2
        global vertex_colors
        vertex_colors.append(VertexColor(term[0], int(term[1]), var))
    elif name.startswith("vertex_bin("):
        term = [v for v in name[11:-1].split(",")]
        assert len(term) == 2
        global vertex_bins
        vertex_bins.append(VertexBin(term[0], int(term[1]), var))
    elif name.startswith("edge_matching_selected("):
        term = [v for v in name[23:-1].split(",")]
        assert len(term) == 2
        global edge_matchings
        edge_matchings.append(EdgeMatching(term[0], term[1], var))
    elif name.startswith("area("):
        global areas
        areas.append(Area(name[5:-1], var))
    elif name.startswith("borderelement("):
        global border_elements
        border_elements.append(BorderElement(name[14:-1], var))
    elif name.startswith("path1("):
        global path_1
        path_1.append(name[6:-1])
    elif name.startswith("path2("):
        global path_2
        path_2.append(name[6:-1])
    elif name.startswith("maxbinsize("):
        global max_bin_size
        max_bin_size = int(name[11:-1])
    elif name.startswith("nrofbins("):
        global num_bins
        num_bins = int(name[9:-1])
    elif name.startswith("nrofcolors("):
        global num_colors
        num_colors = int(name[11:-1])
    elif name.startswith("bin("):
        term = [v for v in name[4:-1].split(",")]
        assert len(term) == 3
        global bin_assignments
        bin_assignments.append(BinAssignment(term[2], int(term[0]), int(term[1]), var))
    return


def onConflict(choice):
    """
    Optional. A conflict happened during the solving
    :param choice: the id of the latest undefined choice according with the previous order, 0 if no choice is undefined
    :return: None
    """
    global num_conflicts
    num_conflicts += 1
    reset_heuristic()


def onFinishedParsing():
    """
    Optional. When the solver finishes the parsing of the input
    :return: (optional) list of literals that must no be removed by initial simplifications
    """
    global input_correct
    input_correct = len(vertices) > 0 and len(edges) > 0 and len(vertex_sizes) > 0 and len(vertex_colors) > 0 \
        and len(vertex_bins) > 0 and max_bin_size != 0 and num_bins != 0 and num_colors != 0 \
        and len(areas) > 0 and len(border_elements) > 0 and len(edge_matchings) > 0

    if not input_correct:
        return

    input_correct = init_data()

    # print "input correct: %s" % input_correct
    # dbg_print_state()


def onStartingSolver(num_vars, num_clauses):
    """
    Optional. When the computation starts (after reading the input and performing the simplifications)
    :param num_vars: number of vars (ids for variables start from 1)
    :param num_clauses: number of clauses
    :return: None
    """
    # set-up interpretation
    global interpretation
    global INT_UNKNOWN
    interpretation = [INT_UNKNOWN] * (num_vars + 1)


def dbg_print_state():
    print "len(edges) = " + str(len(edges))
    print "len(vertex_sizes) = " + str(len(vertex_sizes))
    print "len(vertex_colors) = " + str(len(vertex_colors))
    print "len(vertex_bins) = " + str(len(vertex_bins))
    print "len(areas) = " + str(len(areas))
    print "len(border_elements) = " + str(len(border_elements))
    print "len(path_1) = " + str(len(path_1))
    print "len(path_2) = " + str(len(path_2))
    print "max_bin_size = " + str(max_bin_size)
    print "num_bins = " + str(num_bins)
    print "num_colors = " + str(num_colors)
    print "input_correct = " + str(input_correct)
    print "ordering_valid = " + str(ordering_valid)
    print "current_color = " + str(current_color)
    print "num_conflicts = " + str(num_conflicts)
    print "index = " + str(index)
    print "len(bin_assignments) = " + str(len(bin_assignments))
    print "len(bins_by_color) = " + str(len(bins_by_color))
    print "len(starting_vertices) = " + str(len(starting_vertices))
    print "len(order) = " + str(len(order))
    print "len(path_2) = " + str(len(queue))


def reset_heuristic():
    """
    Reset the heuristic.
    :return: None
    """
    global index
    index = 0

    global vertices
    for v in vertices:
        v.considered = False

    global current_color
    current_color = 0

    global queue
    queue[:] = []


def create_order():
    """
    Create a new ordering
    :return: True if the ordering is correct, False otherwise
    """
    global starting_vertices, order
    if not starting_vertices:
        return False

    logger.debug("order before sorting" + ', '.join([str(v.name) + "(" + str(v.ordering_value) + ")" for v in order]))

    start = starting_vertices.pop(0)

    start.ordering_value += 1
    order = sorted(order, key=lambda v: v.ordering_value, reverse=True)
    start.ordering_value = 0

    logger.debug("order after sorting" + ', '.join([str(v.name) + "(" + str(v.ordering_value) + ")" for v in order]))

    return True

