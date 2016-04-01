%%%%%% P_1  Coloring %%%%%%
% derive vertices of an input graph from edges
vertex(V):-type(V,_). 
vertex(V):-size(V,_).
vertex(V):-edge(V,_). 
vertex(V):-edge(_,V).
% graph coloring
color(1..MaxC):-nrofcolors(MaxC).
1 { vertex_color(V,C):color(C) } 1 :- vertex(V).
% actually used colors
usedcolor(C):- vertex_color(V,C).  

%%%%%% P_2 Bin-Packing %%%%%%
binpacking_color(C):-color(C).
% every vertex must be assigned to exactly one bin
1 { vertex_bin(V,B) : B=1..K, nrofbins(K) } 1 :- vertex(V).
bin(C,B,V):-vertex_color(V,C),vertex_bin(V,B).
% for every bin it holds that the sum of sizes must be smaller or equal to the bin capacity  
:-color(C),nrofbins(K),maxbinsize(MaxS), B=1..K,MaxS+1 #sum{S,V:bin(C,B,V),size(V,S)}.
% actually used bins
usedbin(B) :- bin(C,B,V).

%%%%%% P_3 Disjoint Paths %%%%%%
% colors used in the two paths must be disjoint, i.e. vertices of path1 and path2 cannot be colored in the same color
:-path1(V1), path2(V2), vertex_color(V1,C), vertex_color(V2,C).

%%%%%% P_4 Matching %%%%%%
area(A) :- edge_matching(A,B).
borderelement(B) :- edge_matching(A,B).
% each border element must be assigned to exactly one area
1 { edge_matching_selected(A,B) : edge_matching(A,B) } 1 :- borderelement(B).
% the number of border elements of an area does not exceed the maximal number of border elements
:- area(A),maxborder(MaxB), MaxB+1 { edge_matching_selected(A,B) }.
% all selected border elements of an area must have the same color
edge_matching_color(A,C) :- edge_matching_selected(A,B), vertex_color(B,C).
:- area(A), 2 { edge_matching_color(A,C) }.

%%%%%% P_5 Connectedness %%%%%%
e(X,Y):-edge(X,Y).
e(X,Y):-edge(Y,X).
pred(V1,V2) :- vertex(V1), vertex(V2), V1 < V2, V <= V1 : vertex(V), V < V2.
first(C,V2) :- color(C), pred(V1,V2), not vertex_color(V1,C), first(C,V1) : pred(V,V1).
reachable_color(C,V1) :- color(C), vertex(V1), first(C,V1) : pred(V,V1).
reachable_color(C,V2) :- reachable_color(C,V1), e(V1,V2), vertex_color(V1,C).
:- vertex_color(V,C), not reachable_color(C,V).

#show vertex/1.
#show edge/2.
#show size/2.
#show path1/1.
#show path2/1.
#show nrofcolors/1.
#show nrofbins/1.
#show bin/3.
#show maxbinsize/1.
#show vertex_color/2.
#show vertex_bin/2.
#show bin/3.
#show edge_matching_selected/2.
#show usedcolor/1.
#show usedbin/1.
#show area/1.
#show borderelement/1.
