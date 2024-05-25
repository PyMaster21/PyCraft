
import numpy as np
from moderngl import Context, Program, Buffer


INDEX_ELEMENT_SIZE_LOOKUP = ("B", "H", "I")


class BaseMesh:
    """
    A base class implementing basic mesh functionality
    Every mesh should inherit from this class
    """

    def __init__(self,
                 context: Context,
                 shader: Program,
                 vertex_data: np.array,
                 indices: tuple | list | None,
                 vertex_format: str,
                 attributes: tuple | list,
                 index_element_size: int = 1,
                 dynamic: bool = False) -> None:

        """
        :param context: The rendering context
        :param shader: The shader that will be used with this vao
        :param vertex_data: The vertex data as numpy array
        :param indices: An iterable that will be used as the ibo for this mesh.
        :param vertex_format: The format of the vertex.
        :param attributes: The vbo attributes a.k.a. the name of the vertex's elements. The name must correspond to the
        ones given in the shader.
        :param index_element_size: Must be 1, 2, or 4. This is the buffer_size in bytes of an element of the ibo.
        Smaller buffer_size uses less memory, but allows for indices going up to 2^8-1, 2^16-1, 2^32-1, respectively
        :param dynamic: Set the vbo to be dynamic. A dynamic is updated faster when you write data on it.
        """

        self.ctx = context
        self.shader = shader

        self.index_element_size = index_element_size
        self.dynamic = dynamic

        self.vertex_format = vertex_format
        self.attributes = attributes  # vertex attributes

        if indices is not None:
            self.ibo = self.create_ibo(indices)
        else:
            self.ibo = None

        self.vbo = self.create_vbo(vertex_data)
        self.vao = self.create_vao()

    def render(self) -> None:
        """
        Renders this mesh
        """
        self.vao.render()

    def release(self):
        """
        Releases the mesh resources a.k.a. the ibo, vbo, vao.
        This object is destroyed.
        """
        if self.ibo is not None:
            self.ibo.release()
        self.vbo.release()
        self.vao.release()
        del self

    def create_vao(self):
        """Creates the vao"""
        return self.ctx.vertex_array(self.shader,
                                     [(self.vbo, self.vertex_format, *self.attributes)],
                                     index_buffer=self.ibo,
                                     index_element_size=self.index_element_size)

    def create_ibo(self, indices) -> Buffer:
        """Creates the ibo"""
        return self.ctx.buffer(np.array(indices, dtype=INDEX_ELEMENT_SIZE_LOOKUP[self.index_element_size//2]))

    def create_vbo(self, vertex_data):
        """Creates the vbo"""
        return self.ctx.buffer(vertex_data, dynamic=self.dynamic)

    def update_vbo(self, data: np.array, offset: int):
        """
        Update the vbo content. This operation is faster on dynamic meshes.
        :param data: The data that will be written
        :param offset: The offset in bytes. 0 is the start of the buffer
        """
        self.vbo.write(data, offset=offset)
