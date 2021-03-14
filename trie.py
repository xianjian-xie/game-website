class TrieNode:

    def __init__(self):
        self.word = False
        self.children = {}


class Trie:
    def __init__(self):
        """
        Initialize your data structure here.
        """
        self.root = TrieNode()
        self.returnlist = []

    def insert(self, word: str) -> None:
        """
        Inserts a word into the trie.
        """
        if word == None:
            return
        node = self.root
        for i in range(len(word)):
            if word[i] not in node.children:
                node.children[word[i]] = TrieNode()
            node = node.children[word[i]]

        node.word = True

    def startsWith(self, prefix: str) -> bool:
        """
        Returns if there is any word in the trie that starts with the given prefix.
        """
        node = self.root
        for i in range(len(prefix)):
            if prefix[i].lower() not in node.children and prefix[i].upper() not in node.children:
                return False

            if prefix[i] in node.children:
                node = node.children[prefix[i]]
            elif prefix[i].lower() in node.children:
                node = node.children[prefix[i].lower()]
            elif prefix[i].upper() in node.children:
                node = node.children[prefix[i].upper()]

        return True

    def getData(self, word: str):
        self.returnlist.clear()
        if self.startsWith(word) is False:
            return None
        else:
            node = self.root
            curlist = []
            self.word_backtracking(node, curlist, word, 0)

        return self.returnlist

    def word_backtracking(self, node, curlist, word, index):
        if index == len(word):
            self.backtracking(node, curlist)

        for i in range(index, len(word)):

            if word[i] in node.children.keys():
                temp_node = node.children[word[i]]
                curlist.append(word[i])
                self.word_backtracking(temp_node, curlist, word, i + 1)
                curlist.pop()

            if word[i].lower() in node.children.keys() and word[i].lower() != word[i]:
                temp_node = node.children[word[i].lower()]
                curlist.append(word[i].lower())
                self.word_backtracking(temp_node, curlist, word, i + 1)
                curlist.pop()

            if word[i].upper() in node.children.keys() and word[i].upper() != word[i]:
                temp_node = node.children[word[i].upper()]
                curlist.append(word[i].upper())
                self.word_backtracking(temp_node, curlist, word, i + 1)
                curlist.pop()

            break

    def backtracking(self, node, curlist):
        if node.word:
            self.returnlist.append("".join(curlist))

        if len(node.children) < 1:
            return

        for s in node.children.keys():
            curlist.append(s)
            self.backtracking(node.children[s], curlist)
            curlist.pop()